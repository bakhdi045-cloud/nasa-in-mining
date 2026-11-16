"""Surface-change study: backscatter change, quality bits, temporal reference, references protocol, pipeline.
All data here are SYNTHETIC with known answers."""
from tests import support as s  # noqa: F401  (sets the isolated configuration first)

import json
import math
from pathlib import Path
import shutil
import tempfile
import unittest

import numpy as np
from pydantic import ValidationError

from nasa_in_mining.access import gcov_subset
from nasa_in_mining.mining import stats
from nasa_in_mining.mining.contract import ReferenceEvidence
from nasa_in_mining.surface import backscatter as bs
from nasa_in_mining.surface import boundary, references as refs, study, temporal
from nasa_in_mining.surface.contract import SurfaceStudy
from tests import surface_fixtures as sf

ROOT = Path(__file__).resolve().parents[1]


class StudyContract(unittest.TestCase):
    def test_schema_file_is_in_sync(self):
        recorded = json.loads((ROOT / "contract" / "surface_study.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(recorded, SurfaceStudy.model_json_schema(),
                         "regenerate with: python -m nasa_in_mining contract-schema --kind study --out contract/surface_study.schema.json")


class Backscatter(unittest.TestCase):
    def test_delta_db_known_values(self):
        before = np.array([[1.0, 1.0, 0.5]], "float32")
        after = np.array([[2.0, 0.5, 0.5]], "float32")
        d = bs.delta_db(before, after, np.ones((1, 3), bool))
        np.testing.assert_allclose(d[0], [3.0103, -3.0103, 0.0], atol=1e-3)

    def test_delta_requires_positive_finite_valid_values(self):
        before = np.array([[1.0, 0.0, -1.0, np.nan, 1.0]], "float32")
        after = np.array([[2.0, 2.0, 2.0, 2.0, 2.0]], "float32")
        valid = np.array([[True, True, True, True, False]])
        d = bs.delta_db(before, after, valid)
        self.assertTrue(np.isfinite(d[0, 0]))
        self.assertTrue(np.isnan(d[0, 1:]).all())       # zero, negative, NaN and invalid are never a number

    def test_zone_aggregate_is_linear_power_not_mean_of_db(self):
        before = np.array([[1.0, 1.0]], "float32")
        after = np.array([[1.0, 100.0]], "float32")
        r = bs.zone_delta_db(before, after, np.ones((1, 2), bool), np.ones((1, 2), bool))
        self.assertAlmostEqual(r["aggregate_db"], 10 * math.log10(50.5), places=6)   # mean in linear power first
        self.assertNotAlmostEqual(r["aggregate_db"], 10.0, places=1)                  # mean of the dB values would be 10

    def test_reason_bits_and_aggregation(self):
        power = np.full((4, 4), 0.05, "float32")
        mask = np.ones((4, 4), "uint8")
        exc = np.zeros((4, 4), "uint8")
        mask[0, 0] = 255
        mask[0, 1] = 0
        exc[1, 0] = 2
        power[1, 1] = np.nan
        bits = bs.sample_reasons(power, mask, exc)
        self.assertEqual(bits[0, 0], bs.REASONS["outside_acquisition"])
        self.assertEqual(bits[0, 1], bs.REASONS["not_fully_focused"])
        self.assertEqual(bits[1, 0], bs.REASONS["instrument_anomaly"])
        self.assertEqual(bits[1, 1], bs.REASONS["invalid_value"])
        cell, cbits, n = bs.aggregate_power(power, bits, 2, 0.75)
        self.assertTrue(np.isnan(cell[0, 0]))                                  # 0 valid of 4
        self.assertEqual(cbits[0, 0] & bs.REASONS["insufficient_subpixel_coverage"], 0)   # no valid sample at all
        self.assertTrue(cbits[0, 0] & bs.REASONS["outside_acquisition"])
        self.assertEqual(cbits[1, 1], 0)
        self.assertAlmostEqual(float(cell[1, 1]), 0.05, places=6)
        power2 = power.copy()
        bits2 = bs.sample_reasons(power2, np.ones((4, 4), "uint8"), np.zeros((4, 4), "uint8"))
        bits2[2, 2] = bs.REASONS["invalid_value"]                              # 3 valid of 4 = 0.75: still observed
        self.assertEqual(bs.aggregate_power(power2, bits2, 2, 0.75)[1][1, 1], 0)
        bits2[2, 3] = bs.REASONS["invalid_value"]                              # 2 valid: insufficient coverage
        self.assertTrue(bs.aggregate_power(power2, bits2, 2, 0.75)[1][1, 1] & bs.REASONS["insufficient_subpixel_coverage"])

    def test_validity_bits_of_the_p05036_exception_mask_are_not_anomalies(self):
        power = np.full((2, 2), 0.05, "float32")
        mask = np.ones((2, 2), "uint8")
        exc = np.full((2, 2), 768, "uint16")                      # HH (256) and HV (512) fully focused, no exception code
        self.assertTrue((bs.sample_reasons(power, mask, exc, 256) == 0).all())
        self.assertTrue((bs.sample_reasons(power, mask, exc, 512) == 0).all())
        exc[0, 0] = 512                                            # HH validity bit cleared: partially focused for HH only
        self.assertEqual(bs.sample_reasons(power, mask, exc, 256)[0, 0], bs.REASONS["not_fully_focused"])
        self.assertEqual(bs.sample_reasons(power, mask, exc, 512)[0, 0], 0)
        exc[1, 1] = 768 + 2                                        # a real exception code in the low byte
        self.assertEqual(bs.sample_reasons(power, mask, exc, 256)[1, 1], bs.REASONS["instrument_anomaly"])
        # without the documented validity bits (P05023) any non-zero value is an anomaly, as before
        self.assertEqual(bs.sample_reasons(power, mask, np.full((2, 2), 2, "uint8"))[0, 0], bs.REASONS["instrument_anomaly"])

    def test_noise_floor_is_a_reason_not_a_zero(self):
        p = np.array([[0.001, 0.05]], "float32")
        nebs = np.full((1, 2), 0.0008, "float32")
        bits = bs.mark_noise(p, np.zeros((1, 2), "uint16"), nebs, 2.0)
        self.assertTrue(bits[0, 0] & bs.REASONS["near_noise_floor"])
        self.assertEqual(bits[0, 1], 0)

    def test_expected_speckle_sigma(self):
        self.assertAlmostEqual(bs.expected_speckle_sigma_db(1.0), 10 / math.log(10) * math.sqrt(2), places=9)


class GcovWindow(unittest.TestCase):
    def test_window_edges_are_on_the_20m_grid(self):
        x = 422645.0 + 10.0 * np.arange(200)          # centres at 5 mod 10 -> edges at multiples of 10
        y = 3787915.0 - 10.0 * np.arange(200)
        sl = gcov_subset.aligned_window(x, y, (422700.0, 3786500.0, 423300.0, 3787000.0))
        r, c = sl
        self.assertEqual((x[c.start] - 5) % 20, 0)
        self.assertEqual((y[r.start] + 5) % 20, 0)
        self.assertEqual((c.stop - c.start) % 2, 0)
        self.assertEqual((r.stop - r.start) % 2, 0)


class TemporalReference(unittest.TestCase):
    def test_disjoint_baseline_excludes_shared_acquisitions(self):
        pairs = [("a", "b"), ("b", "c"), ("c", "d"), ("d", "e"), ("e", "f")]
        self.assertEqual(temporal.disjoint_baseline(("c", "d"), pairs), [("a", "b"), ("e", "f")])

    def test_baseline_median_needs_enough_pairs_per_cell(self):
        stack = [np.array([[1.0, np.nan]]), np.array([[3.0, np.nan]]), np.array([[5.0, 1.0]])]
        m = temporal.baseline_median(stack, 3)
        self.assertEqual(m[0, 0], 3.0)
        self.assertTrue(np.isnan(m[0, 1]))

    def test_known_change_is_flagged_and_control_rate_is_measured(self):
        rng = np.random.default_rng(1)
        shape = (200, 200)
        delta = rng.normal(0, 0.5, shape)
        base = np.zeros(shape)
        study_m = np.zeros(shape, bool)
        study_m[:, :100] = True
        control = ~study_m
        delta[50:60, 20:30] -= 4.0                                  # 100 cells, 8 sigma darker
        calib = stats.checkerboard(shape, 20)
        res = temporal.flag_residual(delta.astype("float32"), base.astype("float32"), control, calib, 3.0, 500)
        self.assertEqual(res["status"], "ok")
        self.assertAlmostEqual(res["sigma_db"], 0.5, delta=0.05)
        self.assertGreaterEqual(int((res["flagged"] & (res["direction"] == -1))[50:60, 20:30].sum()), 98)
        self.assertLess(res["evaluation_rate"], 0.01)               # ~0.27 % expected for a Gaussian at 3 sigma
        self.assertEqual(int((res["direction"] == 1)[50:60, 20:30].sum()), 0)

    def test_too_small_control_is_refused(self):
        shape = (20, 20)
        c = np.zeros(shape, bool)
        c[:5] = True
        res = temporal.flag_residual(np.zeros(shape, "float32"), np.zeros(shape, "float32"), c, stats.checkerboard(shape, 2), 3.0, 500)
        self.assertEqual(res["status"], "insufficient_control")


class ReferenceProtocol(unittest.TestCase):
    def _units(self, n_groups=4, per=40):
        units = []
        for g in range(n_groups):
            for stratum, pi in (("flagged_study", 0.5), ("unflagged_study", 0.1)):
                for i in range(per):
                    units.append({"unit_id": f"w{g}:{stratum}:{i}", "window_id": f"w{g}", "stratum": stratum, "group": f"g{g}",
                                  "inclusion_probability": pi, "stratum_frame_size": int(per / pi)})
        return units

    def _ann(self, units, p_f, p_u, source="human", blind=True):
        out = []
        for i, u in enumerate(units):
            p = p_f if u["stratum"].startswith("flagged") else p_u
            lab = "change_visible" if (i * 0.6180339) % 1 < p else "no_change_visible"
            out.append({"unit_id": u["unit_id"], "label": lab, "source": source, "blind_to_radar": blind})
        return out

    def test_frame_strata_and_probabilities(self):
        flagged = np.zeros((30, 30), bool)
        flagged[0:6, 0:6] = True
        valid = np.ones((30, 30), bool)
        valid[24:, 24:] = False
        study_m = np.zeros((30, 30), bool)
        study_m[:, :18] = True
        control = ~study_m
        fr = refs.frame(flagged, valid, study_m, control)
        self.assertEqual(len(fr["flagged_study"]), 4)                   # 6 x 6 cells = 2 x 2 blocks of 3 x 3
        self.assertGreater(len(fr["unflagged_study"]), 20)
        self.assertGreater(len(fr["not_observable"]), 0)
        units, counts = refs.draw({"w": {**fr, "_group": "g"}}, 10, seed=3)
        probs = {u["stratum"]: u["inclusion_probability"] for u in units}
        self.assertEqual(probs["flagged_study"], 1.0)                   # all 4 flagged blocks taken
        self.assertLess(probs["unflagged_study"], 1.0)
        again, _ = refs.draw({"w": {**fr, "_group": "g"}}, 10, seed=3)
        self.assertEqual([u["unit_id"] for u in units], [u["unit_id"] for u in again])   # recorded seed reproduces the draw

    def test_without_annotations_nothing_is_evaluated(self):
        r = refs.evaluate(self._units(), [])
        self.assertEqual(r["status"], "insufficient_reference")
        self.assertIsNone(r["metrics"])

    def test_agent_or_unblinded_annotations_never_count(self):
        units = self._units()
        for src, blind in (("agent", True), ("automated", True), ("human", False)):
            r = refs.evaluate(units, self._ann(units, 0.8, 0.1, source=src, blind=blind))
            self.assertEqual(r["status"], "insufficient_reference", (src, blind))
            self.assertEqual(r["n_annotated_counted"], 0)

    def test_too_few_independent_groups_is_refused(self):
        units = self._units(n_groups=2)
        r = refs.evaluate(units, self._ann(units, 0.8, 0.1))
        self.assertEqual(r["status"], "insufficient_reference")
        self.assertTrue(any("independent_groups" in m for m in r["missing"]))

    def test_weighted_evaluation_known_answer(self):
        units = self._units()
        r = refs.evaluate(units, self._ann(units, 0.8, 0.1), reps=200)
        self.assertEqual(r["status"], "evaluated")
        self.assertAlmostEqual(r["metrics"]["precision"], 0.8, delta=0.08)
        self.assertAlmostEqual(r["metrics"]["miss_rate_among_unflagged"], 0.1, delta=0.06)
        self.assertEqual(r["intervals"]["resampled_unit"], "independent group (optical pair)")
        meta = {"reference_id": "RT", "source": "test", "reviewer": "t", "reviewer_independent": True, "method": "m", "rights": "r",
                "date_start": "2026-01-01", "date_end": "2026-01-02", "geometry_ref": "units.geojson"}
        ref = refs.to_reference_evidence(r, meta, units, "visible_surface_change_at_flagged_cells")
        self.assertIsInstance(ref, ReferenceEvidence)
        self.assertTrue(ref.effective())                                   # test fixture only
        self.assertFalse(refs.to_reference_evidence(r, {**meta, "reviewer_independent": False}, units, "x").effective())


class BoundaryDossier(unittest.TestCase):
    def test_review_states_need_evidence_and_default_is_pending(self):
        tmp = Path(tempfile.mkdtemp(prefix="boundary_"))
        zones = ROOT / "tests" / "_zones.json"
        zpath = tmp / "zones.geojson"
        zpath.write_text(json.dumps(sf.fx._zones()), encoding="utf-8")
        rev = boundary.build(zpath, tmp / "out", None, None, None)
        self.assertEqual(rev["state"], "historical_map")
        self.assertEqual(rev["review"]["status"], "pending_human_review")
        self.assertEqual(rev["classes"]["visible_excavations"], "not_identified")
        inp = tmp / "review.json"
        inp.write_text(json.dumps({"state": "remote_sensing_reviewed", "reviewer": "x"}), encoding="utf-8")
        with self.assertRaises(ValueError):                                # no imagery date, source, evidence
            boundary.build(zpath, tmp / "out2", None, None, inp)
        inp.write_text(json.dumps({"state": "operator_confirmed"}), encoding="utf-8")
        with self.assertRaises(ValueError):
            boundary.build(zpath, tmp / "out3", None, None, inp)


class SurfacePipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="surface_case_"))
        cls.data = cls.tmp / "data"
        sf.series(cls.data, sf.DATES_8, 44, 18, "ascending", change_from=4, bad_date=7)      # 8th date: nothing focused
        sf.series(cls.data, sf.DATES_8[:4], 23, 72, "descending")                            # 4 dates: 3 pairs only
        cls.case = sf.write_case(cls.tmp / "cases" / "syn", [sf.BATCH_ASC, sf.BATCH_DESC])
        cls.study = study.run(cls.case, cls.data, repo_root=cls.tmp, run_id="T1")
        cls.folder = cls.case / "runs" / "T1"

    def win(self, direction, d0):
        return next(w for w in self.study.windows if w.direction == direction and w.before_date == d0)

    def test_contract_round_trip_and_verification(self):
        again = SurfaceStudy.model_validate_json((self.folder / "study.json").read_text(encoding="utf-8"))
        self.assertEqual(again.study_id, "synthetic-surface-test")
        self.assertTrue((self.folder / "VERIFIED").exists())
        self.assertEqual(study.verify_run(self.folder, again), [])
        self.assertTrue((self.case / "output" / "study.json").exists())          # published after verification

    def test_known_step_change_is_measured_and_flagged(self):
        w = self.win("ascending", sf.DATES_8[3])                                 # (d3, d4): the darkening happens here
        hh = next(p for p in w.pols if p.pol == "HH")
        self.assertEqual(hh.baseline.status, "ok")
        self.assertGreaterEqual(hh.baseline.n_pairs, 3)
        self.assertLess(hh.flags.darker_area_km2.value, 0.30)
        self.assertGreater(hh.flags.darker_area_km2.value, 0.22)                 # 0.25 km2 darkened by 3.98 dB
        self.assertLess(hh.flags.brighter_area_km2.value, 0.02)
        self.assertGreater(hh.flags.ratio.value, 5)
        quiet = self.win("ascending", sf.DATES_8[1])
        self.assertLess(next(p for p in quiet.pols if p.pol == "HH").flags.darker_area_km2.value, 0.05)
        agg = next(z for z in hh.zones if z.zone_id == "study").aggregate_db.value
        expected = 10 * math.log10((0.9375 + 0.0625 * 0.4))                       # 6.25 % of the study area darkened
        self.assertAlmostEqual(agg, expected, delta=0.05)

    def test_insufficient_baseline_is_stated_not_zero(self):
        w = self.win("descending", sf.DATES_8[0])
        hh = next(p for p in w.pols if p.pol == "HH")
        self.assertEqual(hh.baseline.status, "insufficient_baseline")
        self.assertIsNone(hh.flags)
        self.assertIsNotNone(hh.study_minus_control_db.value)                    # the descriptive change is still given
        c = next(c for c in self.study.conclusions if c.zone_id == "study")
        self.assertEqual(c.radar_variation, "measured")                          # from the ascending windows

    def test_rejected_date_keeps_its_quality_layer_and_its_reasons(self):
        bad = next(a for a in self.study.acquisitions if a.status == "rejected")
        self.assertIn("not_fully_focused", bad.reasons)
        for d0 in (sf.DATES_8[6], sf.DATES_8[7]):
            w = self.win("ascending", d0)
            self.assertEqual(w.status, "rejected")
            self.assertTrue(w.quality_layer_id)
            self.assertTrue((self.folder / next(l.url for l in self.study.layers if l.id == w.quality_layer_id)).exists())
            self.assertTrue(all(p.status == "unavailable" and p.flags is None for p in w.pols))
        import rasterio
        with rasterio.open(self.folder / "rasters" / f"quality_HH_{self.win('ascending', sf.DATES_8[6]).window_id}.tif") as src:
            q = src.read(1)
        self.assertTrue((q != 0).mean() > 0.99)                                  # every cell carries a reason, none is "stable"

    def test_quality_bits_agree_with_the_statistics_mask(self):
        w = self.win("ascending", sf.DATES_8[3])
        import rasterio
        with rasterio.open(self.folder / "rasters" / f"quality_HH_{w.window_id}.tif") as src:
            q = src.read(1)
        with rasterio.open(self.folder / "rasters" / f"delta_db_HH_{w.window_id}.tif") as src:
            d = src.read(1, masked=True)
            self.assertEqual(src.scales[0], 0.05)
        self.assertTrue(((q == 0) == ~np.ma.getmaskarray(d)).all())              # same pixels in the layer and the numbers
        decoded = d.astype("float64") * 0.05                                      # the scale of the file gives dB
        self.assertLess(abs(float(np.ma.median(decoded[np.ma.getmaskarray(d) == 0]))), 1.0)   # a quiet window: small variations

    def test_hv_noise_exclusion_is_a_reason(self):
        w = self.win("ascending", sf.DATES_8[1])
        hv = next(p for p in w.pols if p.pol == "HV")
        self.assertEqual(next(z for z in hv.zones if z.zone_id == "study").observed_fraction.value, 1.0)   # NEBS far below the power

    def test_reference_state_is_pending_and_blind_packet_hides_radar(self):
        self.assertEqual(self.study.references.status, "awaiting_annotations")
        self.assertEqual(self.study.evidence.references, [])
        packet = json.loads((self.folder / "annotation" / "units_for_annotators.geojson").read_text(encoding="utf-8"))
        text = json.dumps(packet)
        for word in ("flagged", "stratum", "radar", "darker"):
            self.assertNotIn(word, text)

    def test_evaluated_state_or_reviewed_boundary_cannot_be_declared_by_label(self):
        data = json.loads((self.folder / "study.json").read_text(encoding="utf-8"))
        data["references"]["status"] = "evaluated"                       # a label, with no effective structured reference
        with self.assertRaises(ValidationError):
            SurfaceStudy.model_validate(data)
        data = json.loads((self.folder / "study.json").read_text(encoding="utf-8"))
        data["boundary"]["state"] = "remote_sensing_reviewed"            # a state, with the review still pending
        with self.assertRaises(ValidationError):
            SurfaceStudy.model_validate(data)

    def test_no_validation_language_in_the_report(self):
        html = (self.folder / "report" / "report.html").read_text(encoding="utf-8")
        self.assertIn("étude exploratoire calculée", html)
        self.assertNotIn("validée par", html.lower())

    def test_incompatible_grid_is_rejected_not_resampled(self):
        tmp = Path(tempfile.mkdtemp(prefix="surface_grid_"))
        data = tmp / "data"
        sf.series(data, sf.DATES_8[:5], 44, 18, "ascending", shift_date=2)
        case = sf.write_case(tmp / "cases" / "syn", [sf.BATCH_ASC])
        st = study.run(case, data, repo_root=tmp, run_id="G1", publish=False)
        bad = next(a for a in st.acquisitions if a.acquisition_id.endswith("20260125"))
        self.assertEqual((bad.status, bad.reasons), ("rejected", ["incompatible_grid"]))

    def test_modified_crop_is_detected(self):
        tmp = Path(tempfile.mkdtemp(prefix="surface_mod_"))
        data = tmp / "data"
        sf.series(data, sf.DATES_8[:3], 44, 18, "ascending")
        f = next((data / "GCOV").iterdir()) / "HHHH.tif"
        f.write_bytes(b"corrupt")
        case = sf.write_case(tmp / "cases" / "syn", [sf.BATCH_ASC])
        with self.assertRaises(Exception):
            study.run(case, data, repo_root=tmp, run_id="M1", publish=False)


if __name__ == "__main__":
    unittest.main()
