"""Mining-case pipeline, contract and API, on SYNTHETIC data with exactly known answers."""
from tests import support as s  # noqa: F401  (sets the isolated configuration first)

import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from pydantic import ValidationError

from nasa_in_mining.mining import coherence_change as cc
from nasa_in_mining.mining import contract, pipeline
from tests import mining_fixtures as fx

ROOT = Path(__file__).resolve().parents[1]


def run_synthetic(**kw):
    tmp = Path(tempfile.mkdtemp(prefix="mining_case_"))
    case = fx.write_case(tmp / "cases" / "synthetic")
    data = fx.write_data(tmp / "data", **kw)
    return pipeline.run(case, data, case / "output", repo_root=tmp), case


class CoherenceFunctions(unittest.TestCase):
    def test_mask_decoding(self):
        m = np.array([11, 12, 111, 10, 1, 255, 11 | (1 << 9)], dtype="uint32")
        self.assertEqual(cc.mask_valid(m).tolist(), [True, True, False, False, False, False, True])
        self.assertEqual(cc.anomaly_flags(m).tolist(), [False] * 6 + [True])

    def test_threshold_follows_control_and_needs_enough_pixels(self):
        coh = np.full((100, 100), 0.8, "float32")
        control = np.zeros_like(coh, bool)
        control[:, :50] = True
        out = cc.flag_pair(coh, np.ones_like(control), control, 0.01)
        self.assertEqual(out["status"], "ok")
        self.assertAlmostEqual(out["threshold"], 0.8)
        self.assertEqual(int(out["flagged"].sum()), 0)
        small = np.zeros_like(control)
        small[:10, :10] = True
        self.assertEqual(cc.flag_pair(coh, np.ones_like(control), small, 0.01)["status"], "insufficient_control")
        with self.assertRaises(ValueError):
            cc.flag_pair(coh, np.ones_like(control), control, 0.7)
        with self.assertRaises(ValueError):
            cc.flag_pair(coh, np.ones((5, 5), bool), control, 0.01)

    def test_unobserved_zone_is_not_unchanged(self):
        zone = np.ones((4, 4), bool)
        out = cc.zone_stats(np.zeros((4, 4), bool), np.zeros((4, 4), bool), zone, np.zeros((4, 4)), 0.0004)
        self.assertEqual(out["observable_fraction"], 0)
        self.assertIsNone(out["flagged_area_km2"])
        self.assertIsNone(out["flagged_fraction_of_observable"])
        empty = cc.zone_stats(None, np.ones((4, 4), bool), np.zeros((4, 4), bool), np.zeros((4, 4)), 0.0004)
        self.assertIsNone(empty["observable_fraction"])

    def test_recurrence_counts_only_observed_pairs(self):
        f1, f2 = np.array([[True, False]]), np.array([[True, True]])
        v1, v2 = np.array([[True, True]]), np.array([[True, False]])
        frac, seen = cc.recurrence([f1, f2], [v1, v2])
        self.assertEqual(frac.tolist(), [[1.0, 0.0]])
        self.assertEqual(seen.tolist(), [[2, 1]])

    def test_lift_and_clusters(self):
        a = np.zeros((10, 10), bool); a[:2, :2] = True
        b = np.zeros((10, 10), bool); b[:2, :2] = True; b[9, 9] = True
        out = cc.lift(a, b, np.ones((10, 10), bool))
        self.assertAlmostEqual(out["p_b_given_a"], 1.0)
        self.assertAlmostEqual(out["lift"], 96.0)
        labels, clusters = cc.change_zones(b, np.ones((10, 10), bool), np.zeros((10, 10)), min_pixels=2)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0]["pixels"], 4)


class ContractRules(unittest.TestCase):
    def test_absent_and_zero_are_distinct(self):
        self.assertEqual(contract.measured(0, "km2").value, 0.0)
        with self.assertRaises(ValidationError):
            contract.Measurement(value=None, unit="km2", status="measured")
        with self.assertRaises(ValidationError):
            contract.Measurement(value=None, unit="km2", status="unavailable")          # a reason is required
        with self.assertRaises(ValidationError):
            contract.Measurement(value=1.0, unit="km2", status="not_measured")

    def test_uncertainty_zero_must_state_its_method(self):
        with self.assertRaises(ValidationError):
            contract.Uncertainty(kind="empirical_sigma", value=0.0)
        self.assertIsNone(contract.measured(1, "cm").uncertainty)
        with self.assertRaises(ValidationError):
            contract.Uncertainty(kind="not_estimated", value=0.0)

    def test_schema_file_is_in_sync(self):
        recorded = json.loads((ROOT / "contract" / "mining_case.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(recorded, contract.MiningCase.model_json_schema(),
                         "regenerate with: python -m nasa_in_mining contract-schema --out contract/mining_case.schema.json")

    def test_recorded_real_case_satisfies_contract(self):
        path = ROOT / "cases" / "benguerir" / "output" / "case.json"
        if not path.exists():
            self.skipTest("no recorded Benguerir case in this checkout")
        case = contract.MiningCase.model_validate_json(path.read_text(encoding="utf-8"))
        self.assertEqual(case.data_nature, "real")
        for layer in case.layers:
            if layer.id.startswith("coh_"):
                continue                     # large coherence previews are regenerated locally, not versioned
            self.assertTrue((path.parent / layer.url).is_file(), layer.url)


class SyntheticPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case, cls.dir = run_synthetic()

    def pair(self, i):
        a, b = fx.DATES[i]
        return next(p for p in self.case.pairs if p.reference_date == f"{a[:4]}-{a[4:6]}-{a[6:]}")

    def zone(self, p, zid="study"):
        return next(z for z in p.zones if z.zone_id == zid)

    def test_known_change_area_and_unobserved_pixels(self):
        p = self.pair(1)
        z = self.zone(p)
        self.assertEqual(p.status, "ok")
        self.assertAlmostEqual(p.threshold.value, 0.8, places=6)
        self.assertAlmostEqual(z.flagged_area_km2.value, fx.CHANGE_KM2, places=9)
        self.assertAlmostEqual(z.observable_fraction.value, 1 - 100 / fx.STUDY_PIXELS, places=9)
        self.assertEqual(p.n_clusters, 1)
        self.assertAlmostEqual(p.clusters_shown[0].area_km2, fx.CHANGE_KM2, places=9)

    def test_no_change_is_a_measured_zero(self):
        z = self.zone(self.pair(0))
        self.assertEqual(z.flagged_area_km2.status, "measured")
        self.assertEqual(z.flagged_area_km2.value, 0.0)

    def test_measured_zero_coherence_is_flagged_not_missing(self):
        self.assertAlmostEqual(self.zone(self.pair(2)).flagged_area_km2.value, fx.CHANGE_KM2, places=9)

    def test_missing_optical_reference_is_explicit(self):
        self.assertEqual(self.case.processing.status, "partial")
        self.assertIn("blocker.no_optical_reference", self.case.processing.blockers)
        self.assertTrue(all(p.optical is None for p in self.case.pairs))
        self.assertEqual(self.case.data_nature, "synthetic")

    def test_recurrence_and_exports_with_provenance(self):
        g = self.case.geometries[0]
        self.assertEqual(len(g.recurrence_pairs), 3)
        self.assertAlmostEqual(g.study_area_flagged_ever_km2.value, fx.CHANGE_KM2, places=9)
        self.assertAlmostEqual(g.study_area_flagged_half_or_more_km2.value, fx.CHANGE_KM2, places=9)
        out = self.dir / "output"
        for e in self.case.exports:
            self.assertTrue((out / e.path).is_file(), e.path)
        self.assertTrue(self.case.manifest.inputs)
        self.assertEqual(self.case.cross_geometry.status, "unavailable")
        with open(out / "case.json", encoding="utf-8") as f:
            contract.MiningCase.model_validate(json.load(f))

    def test_los_is_marked_unverified(self):
        self.assertTrue(all(lp.sign_verified is False for lp in self.case.los))
        v = {x.observable: x.level for x in self.case.validation}
        self.assertEqual(v["cause_of_change"], "not_computed")


class SyntheticFailures(unittest.TestCase):
    def test_incompatible_grid_is_reported_not_resampled(self):
        case, _ = run_synthetic(incompatible=True)
        self.assertIn("incompatible_grid", [p.status for p in case.pairs])

    def test_quality_rejection_is_reported(self):
        case, _ = run_synthetic(rejected=True)
        rej = [p for p in case.pairs if p.status == "rejected_quality"]
        self.assertEqual(len(rej), 1)
        self.assertIsNone(rej[0].threshold.value)
        self.assertEqual(rej[0].threshold.status, "not_measured")

    def test_no_products_gives_an_unavailable_case(self):
        tmp = Path(tempfile.mkdtemp(prefix="mining_empty_"))
        case_dir = fx.write_case(tmp / "cases" / "synthetic")
        (tmp / "data").mkdir()
        case = pipeline.run(case_dir, tmp / "data", case_dir / "output", repo_root=tmp)
        self.assertEqual(case.processing.status, "unavailable")
        self.assertEqual(case.pairs, [])
        self.assertIn("limit.no_data_is_not_no_change", case.limits)
        self.assertEqual(case.validation[0].level, "not_computed")


class Api(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from nasa_in_mining.api import create_app
        cls.case, cls.dir = run_synthetic()
        cls.cases_root = cls.dir.parent
        cls.client = TestClient(create_app(cls.cases_root, cls.cases_root / "no_web"))

    def test_health_and_list(self):
        h = self.client.get("/api/health").json()
        self.assertEqual(h["schema_version"], "1.0")
        lst = self.client.get("/api/cases").json()
        self.assertEqual(lst[0]["case_id"], "synthetic-test")
        self.assertEqual(lst[0]["data_nature"], "synthetic")

    def test_case_round_trip_equals_file(self):
        body = self.client.get("/api/cases/synthetic-test").json()
        on_disk = json.loads((self.dir / "output" / "case.json").read_text(encoding="utf-8"))
        self.assertEqual(body, on_disk)

    def test_errors_are_explicit(self):
        r = self.client.get("/api/cases/unknown")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["error"], "case_not_found")
        r = self.client.get("/api/cases/synthetic-test/files/../case_config.json")
        self.assertEqual(r.status_code, 404)
        r = self.client.get("/api/cases/synthetic-test/files/exports/pairs.csv")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.head("/api/cases/synthetic-test/files/exports/pairs.csv").status_code, 200)

    def test_contract_violation_is_reported(self):
        tmp = Path(tempfile.mkdtemp(prefix="mining_bad_"))
        out = tmp / "bad" / "output"
        out.mkdir(parents=True)
        data = json.loads((self.dir / "output" / "case.json").read_text(encoding="utf-8"))
        data["case_id"] = "bad"
        data["pairs"][1]["zones"][0]["flagged_area_km2"] = {"value": None, "unit": "km2", "status": "measured"}
        (out / "case.json").write_text(json.dumps(data), encoding="utf-8")
        from fastapi.testclient import TestClient
        from nasa_in_mining.api import create_app
        r = TestClient(create_app(tmp)).get("/api/cases/bad")
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.json()["error"], "contract_violation")


if __name__ == "__main__":
    unittest.main()
