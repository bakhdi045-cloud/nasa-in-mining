from tests import support as s

import json
import unittest

import numpy as np
from pyproj import Transformer
from rasterio.transform import from_origin

from nasa_in_mining.roi import load_polygons, summarize_raster


class PolygonTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.tmp = tempfile.TemporaryDirectory(prefix="mining_roi_")
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.transform = from_origin(500000, 3500000, 10, 10)
        self.path = self.folder / "signal.tif"
        s.write_tif(self.path, np.arange(16, dtype="float32").reshape(4, 4), self.transform)
        self.roi = self.folder / "boundary.geojson"
        self.write_roi([(0, 0), (2, 0), (2, 4), (0, 4), (0, 0)])

    def write_roi(self, pixels):
        to_ll = Transformer.from_crs(32629, 4326, always_xy=True)
        coords = [list(to_ll.transform(*(self.transform * p))) for p in pixels]
        self.roi.write_text(json.dumps({"type": "Polygon", "coordinates": [coords]}), encoding="utf-8")

    def test_polygon_statistics_known_area_and_selection(self):
        out = summarize_raster(self.path, self.roi, "coherence", threshold=7)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["inside_pixels"], 8)
        self.assertAlmostEqual(out["sampled_area_km2"], 0.0008)
        self.assertAlmostEqual(out["selected_area_km2"], 0.0004)
        self.assertEqual(out["statistics"]["median"], 6.5)
        self.assertIsNone(out["uncertainty"])

    def test_zero_change_is_different_from_missing_data(self):
        s.write_tif(self.path, np.zeros((4, 4), dtype="float32"), self.transform)
        out = summarize_raster(self.path, self.roi, "cm", threshold=0.1)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["statistics"]["median"], 0)
        self.assertEqual(out["selected_area_km2"], 0)

    def test_nodata_is_not_stable_ground(self):
        s.write_tif(self.path, np.full((4, 4), np.nan, dtype="float32"), self.transform)
        out = summarize_raster(self.path, self.roi, "cm", threshold=0.1)
        self.assertEqual(out["status"], "no_data")
        self.assertEqual(out["valid_fraction"], 0)
        self.assertIsNone(out["statistics"])
        self.assertIsNone(out["selected_area_km2"])

    def test_outside_roi_has_no_sampled_pixels(self):
        self.write_roi([(10, 10), (12, 10), (12, 12), (10, 12), (10, 10)])
        out = summarize_raster(self.path, self.roi, "cm")
        self.assertEqual(out["status"], "no_sampled_pixels")
        self.assertIsNone(out["valid_fraction"])

    def test_geographic_area_is_not_degrees_squared(self):
        transform = from_origin(-8, 33, 0.001, 0.001)
        s.write_tif(self.path, np.ones((2, 2), dtype="float32"), transform, "EPSG:4326")
        coords = [[-8, 33], [-7.998, 33], [-7.998, 32.998], [-8, 32.998], [-8, 33]]
        self.roi.write_text(json.dumps({"type": "Polygon", "coordinates": [coords]}), encoding="utf-8")
        out = summarize_raster(self.path, self.roi, "cm")
        self.assertEqual(out["area_method"], "geodesic_pixel_area")
        self.assertGreater(out["sampled_area_km2"], 0.03)
        self.assertLess(out["sampled_area_km2"], 0.05)

    def test_geojson_feature_collection(self):
        geom = json.loads(self.roi.read_text())
        self.roi.write_text(json.dumps({"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {"source": "synthetic test boundary"}, "geometry": geom}
        ]}), encoding="utf-8")
        self.assertEqual(len(load_polygons(self.roi)), 1)

    def test_unclosed_boundary_and_point_are_rejected(self):
        self.roi.write_text(json.dumps({"type": "Point", "coordinates": [-8, 33]}), encoding="utf-8")
        with self.assertRaises(ValueError):
            load_polygons(self.roi)
        self.roi.write_text(json.dumps({"type": "Polygon", "coordinates": [
            [[-8, 33], [-7, 33], [-7, 32], [-8, 32]]]}), encoding="utf-8")
        with self.assertRaises(ValueError):
            load_polygons(self.roi)

    def test_unknown_units_or_invalid_threshold_rejected(self):
        with self.assertRaises(ValueError):
            summarize_raster(self.path, self.roi, "")
        with self.assertRaises(ValueError):
            summarize_raster(self.path, self.roi, "cm", float("inf"))
