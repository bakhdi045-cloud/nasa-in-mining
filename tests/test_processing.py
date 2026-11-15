from __future__ import annotations

from tests import support as s

import ast
import importlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from nasa_in_mining import catalog, config, exposure, quality, uncertainty
from nasa_in_mining.analysis import analyze_point, event_stamp
from nasa_in_mining.cli import json_safe
from nasa_in_mining.recipes import corrections, displacement, timeseries, wavelength


class ProcessingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        s.make_products(config.DATA_DIR)
        cls.products = catalog.refresh()

    def test_catalog_reads_real_layout_and_version(self):
        self.assertEqual(len(self.products), 3)
        self.assertEqual(self.products[0].series_key, (44, 17, "P05023"))
        self.assertEqual(self.products[0].maturity, "provisional")
        self.assertEqual(self.products[0].span_days, 12)
        self.assertTrue(all(p.covers(s.LAT, s.LON) for p in self.products))

    def test_quality_rejects_flat_and_low_coherence(self):
        a = np.linspace(-1, 1, 10000).reshape(100, 100)
        self.assertFalse(quality.assess(np.zeros_like(a), np.ones_like(a))["ok"])
        self.assertFalse(quality.assess(a, np.full_like(a, 0.05))["ok"])
        self.assertTrue(quality.assess(a, np.full_like(a, 0.8))["ok"])

    def test_robust_noise_does_not_follow_an_outlier(self):
        a = np.linspace(-1, 1, 1001)
        before = uncertainty.robust_sigma(a)
        a[-1] = 1e9
        self.assertAlmostEqual(uncertainty.robust_sigma(a), before)

    def test_frequency_from_product_controls_displacement(self):
        p = self.products[-1]
        wl, source = wavelength.wavelength_m(p)
        self.assertAlmostEqual(wl, 299_792_458 / s.FREQ)
        self.assertIn("centerFrequency", source)
        ans = displacement.analyze(p, s.LAT, s.LON, make_layer=False)
        self.assertAlmostEqual(ans["los_cm"], 2.0, delta=0.4)

    def test_missing_frequency_has_a_recorded_fallback(self):
        folder = s.ROOT / "without_frequency"
        folder.mkdir(exist_ok=True)
        value, source = wavelength._for_folder(folder)
        self.assertEqual(value, config.WAVELENGTH_M)
        self.assertIn("no centerFrequency", source)

    def test_iono_mask_and_metre_conversion(self):
        phase, description = corrections.to_radians(np.array([1.0]), "m", 0.25)
        self.assertAlmostEqual(float(phase[0]), -16 * np.pi)
        self.assertIn("metres converted", description)
        self.assertEqual(corrections.uncertainty_mask(np.array([0.2, 2.0])).tolist(), [False, True])

    def test_correcting_phase_preserves_nan_screen_convention(self):
        out = corrections.correct_iono(np.array([3.0, 4.0]), np.array([1.0, np.nan]))
        np.testing.assert_array_equal(out, [2.0, 4.0])

    def test_surface_change_runs_end_to_end_and_is_not_a_mine_polygon(self):
        out = analyze_point("surface-change", s.LAT, s.LON)
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual(out["scope"], {"kind": "circle", "radius_m": 5000})
        self.assertGreater(out["result"]["changed_km2_5km"], 0)
        self.assertEqual(out["validation"], "not_independently_validated")
        layer = out["result"]["layer"]
        self.assertTrue((config.CACHE_DIR / "layers" / Path(layer["url"]).name).is_file())

    def test_point_series_no_annual_rate_from_a_short_record(self):
        out = analyze_point("timeseries", s.LAT, s.LON)
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual(out["result"][0]["n_pairs"], 3)
        self.assertIsNone(out["result"][0]["velocity_mm_yr"])
        self.assertFalse(out["los_sign_verified"])

    def test_disconnected_pairs_are_separate_components(self):
        from dataclasses import replace
        p = self.products[0]
        unrelated = replace(p, ref="20280101T000000", sec="20280113T000000")
        comps = timeseries._components([p, unrelated])
        self.assertEqual(len(comps), 2)
        self.assertTrue(comps[0].isdisjoint(comps[1]))

    def test_no_coverage_is_not_a_zero_measurement(self):
        out = analyze_point("displacement", -80.0, 150.0)
        self.assertEqual(out["status"], "no_coverage")
        self.assertIsNone(out["result"])

    def test_bad_coordinates_are_rejected(self):
        with self.assertRaises(ValueError):
            analyze_point("displacement", float("nan"), s.LON)

    def test_point_recipe_rejects_degree_pixels_before_metric_windowing(self):
        from dataclasses import replace
        from rasterio.transform import from_origin
        path = s.ROOT / "degrees.tif"
        s.write_tif(path, np.ones((4, 4), dtype="float32"), from_origin(-8, 33, 0.01, 0.01), "EPSG:4326")
        wrong = replace(self.products[0], files={"phase": path})
        with patch.object(catalog, "find", return_value=[wrong]), self.assertRaisesRegex(ValueError, "reproject"):
            analyze_point("displacement", s.LAT, s.LON)

    def test_gcov_flood_recipe_on_local_files(self):
        for day, after in (("20260101", False), ("20260113", True)):
            folder = s.product_dir(config.DATA_DIR, "GCOV", day, day)
            hh = np.full(s.BUMP.shape, 0.1, "float32")
            if after:
                hh[s.BUMP > 0.5] = 0.001
            s.write_tif(folder / "HHHH.tif", hh)
            s.write_tif(folder / "HVHV.tif", np.full_like(hh, 0.03))
            (folder / "_DONE").write_text("{}")
        catalog.refresh()
        out = analyze_point("flood", s.LAT, s.LON)
        self.assertEqual(out["status"], "ok", out)
        self.assertGreater(out["result"]["open_water_ha"], 0)

    def test_goff_offset_recipe_on_local_files(self):
        folder = s.product_dir(config.DATA_DIR, "GOFF", "20260101", "20260113")
        s.write_tif(folder / "alongTrackOffset.tif", np.full(s.BUMP.shape, 3, "float32"))
        s.write_tif(folder / "slantRangeOffset.tif", np.zeros(s.BUMP.shape, "float32"))
        s.write_tif(folder / "correlationSurfacePeak.tif", np.ones(s.BUMP.shape, "float32"))
        (folder / "_DONE").write_text("{}")
        catalog.refresh()
        out = analyze_point("offsets", s.LAT, s.LON)
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual(out["result"]["magnitude_m"], 3)

    def test_sme2_reads_final_soil_moisture_and_its_uncertainty(self):
        import h5py
        folder = s.product_dir(config.DATA_DIR, "SME2", "20260105", "20260105")
        with h5py.File(folder / "soil.h5", "w") as h5:
            g = h5.create_group("science/LSAR/SME2/grids")
            g.create_dataset("soilMoisture", data=np.full(s.BUMP.shape, 0.25, "float32"))
            g.create_dataset("soilMoistureUncertainty", data=np.full(s.BUMP.shape, 0.04, "float32"))
            g.create_dataset("xCoordinates", data=s.X + (np.arange(s.N) + 0.5 - s.N / 2) * s.PX)
            g.create_dataset("yCoordinates", data=s.Y - (np.arange(s.N) + 0.5 - s.N / 2) * s.PX)
            g.create_dataset("projection", data=32629)
        (folder / "_DONE").write_text("{}")
        catalog.refresh()
        out = analyze_point("soil-moisture", s.LAT, s.LON)
        self.assertEqual(out["status"], "ok", out)
        self.assertEqual(out["result"]["latest_m3m3"], 0.25)
        self.assertAlmostEqual(out["result"]["uncertainty_m3m3"], 0.04)

    def test_date_only_does_not_become_an_exact_instant(self):
        self.assertEqual(event_stamp("2026-01-20"), ("20260120T000000", "day"))
        self.assertEqual(event_stamp("2026-01-20T12:00:00+01:00"), ("20260120T110000", "exact"))
        with self.assertRaises(ValueError):
            event_stamp("2026-01-20T12:00:00")

    def test_exposure_counts_are_masked_not_projected_as_danger(self):
        from rasterio.transform import from_origin
        grid = exposure.Grid(from_origin(500_000, 850_000, 100, 100), "EPSG:32629", (4, 4))
        mask = np.ones((4, 4), dtype=bool)
        self.assertAlmostEqual(exposure.area_km2(mask, grid), 0.16)
        self.assertEqual(exposure.with_spread({"buildings": 5}, [{"buildings": 3}, {"buildings": 6}])
                         ["buildings"]["uncertainty"], 2)

    def test_offline_external_helpers_do_not_make_http_requests(self):
        with patch("requests.get", side_effect=AssertionError("unexpected HTTP GET")), \
             patch("requests.post", side_effect=AssertionError("unexpected HTTP POST")):
            with self.assertRaises(exposure.ExposureError):
                exposure.population_source("ZZZ")
            with self.assertRaises(exposure.ExposureError):
                exposure._osm_tile(0.0, 0.0, 0.25, 0.25)

    def test_strict_json_preserves_zero_and_replaces_nonfinite_with_null(self):
        value = json_safe({"zero": 0.0, "missing": np.nan, "nested": np.array([0.0, np.inf])})
        self.assertEqual(value, {"zero": 0.0, "missing": None, "nested": [0.0, None]})
        json.dumps(value, allow_nan=False)

    def test_all_extracted_imports_and_hashes_are_local(self):
        import hashlib
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / "UPSTREAM.json").read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["files"]), 16)
        for entry in manifest["files"]:
            path = root / entry["destination"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry["extracted_sha256"])
            if path.suffix != ".py":
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn((node.module or "").split(".")[0],
                                     {"config", "catalog", "raster", "quality", "uncertainty", "recipes", "science"})
            module = entry["destination"].removeprefix("src/").removesuffix(".py").replace("/", ".")
            imported = importlib.import_module(module)
            self.assertTrue(Path(imported.__file__).resolve().is_relative_to(root))
