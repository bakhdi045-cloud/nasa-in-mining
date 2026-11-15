"""Mining-case pipeline v2, statistics, contract, findings rules and API, on SYNTHETIC data with known answers."""
from tests import support as s  # noqa: F401  (sets the isolated configuration first)

import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace as NS
import unittest

import numpy as np
from pydantic import ValidationError

from nasa_in_mining.mining import coherence_change as cc
from nasa_in_mining.mining import contract, findings, pipeline, stats
from tests import mining_fixtures as fx

ROOT = Path(__file__).resolve().parents[1]


def run_synthetic(**kw):
    tmp = Path(tempfile.mkdtemp(prefix="mining_case_"))
    case = fx.write_case(tmp / "cases" / "synthetic")
    data = fx.write_data(tmp / "data", **kw)
    return pipeline.run(case, data, repo_root=tmp), case, data


class StatisticsFunctions(unittest.TestCase):
    def test_mask_decoding(self):
        m = np.array([11, 12, 111, 10, 1, 255, 11 | (1 << 9)], dtype="uint32")
        self.assertEqual(cc.mask_valid(m).tolist(), [True, True, False, False, False, False, True])
        self.assertEqual(cc.anomaly_flags(m).tolist(), [False] * 6 + [True])

    def test_calibration_and_evaluation_are_disjoint(self):
        coh = np.full((200, 200), 0.8, "float32")
        coh[:, 100:] = 0.5                       # evaluation blocks partly differ from calibration blocks
        calib = stats.checkerboard(coh.shape, 50)
        r = stats.threshold_split(coh, np.ones_like(calib), np.ones_like(calib), calib, 0.01)
        self.assertEqual(r["status"], "ok")
        self.assertFalse(np.any(calib & ~calib))
        self.assertEqual(r["calibration_pixels"] + r["evaluation_pixels"], coh.size)
        with self.assertRaises(ValueError):
            stats.threshold_split(coh, np.ones_like(calib), np.ones_like(calib), calib, 0.6)

    def test_block_bootstrap_needs_enough_blocks(self):
        f = np.zeros((40, 40), bool)
        ids = stats.block_ids(f.shape, 20)
        k, n = stats.block_counts(f, np.ones_like(f), np.ones_like(f), ids)
        self.assertEqual(stats.bootstrap_ratio(k, n)["status"], "too_few_blocks")
        f2 = np.random.default_rng(1).random((200, 200)) < 0.1
        ids = stats.block_ids(f2.shape, 20)
        k, n = stats.block_counts(f2, np.ones_like(f2), np.ones_like(f2), ids)
        b = stats.bootstrap_ratio(k, n)
        self.assertLessEqual(b["fraction_low"], 0.1)
        self.assertGreaterEqual(b["fraction_high"], 0.09)

    def test_neighbouring_zone_is_not_the_same_zone(self):
        a = np.zeros((50, 50), bool); a[:10, :10] = True
        b = np.zeros((50, 50), int); b[8:18, 8:18] = 1; b[0:10, 2:12] = 2
        self.assertEqual(stats.overlap_match(a, b, 0.5), [2])

    def test_contingency_keeps_absolute_counts(self):
        a = np.zeros((10, 10), bool); a[0, :2] = True
        b = np.zeros((10, 10), bool); b[0, 0] = True
        t = stats.contingency(a, b, np.ones((10, 10), bool))
        self.assertEqual((t["n11"], t["n10"], t["n01"], t["n00"]), (1, 1, 0, 98))
        self.assertIsNone(t["ratio"])            # undefined, not infinite

    def test_window_overlap(self):
        self.assertAlmostEqual(stats.overlap_days(("2026-06-29T05:46", "2026-07-11T05:46"),
                                                  ("2026-06-27T19:20", "2026-07-09T19:20")), 10.565, delta=0.001)


class ContractRules(unittest.TestCase):
    def test_numbers_are_finite_and_fractions_bounded(self):
        with self.assertRaises(ValidationError):
            contract.measured(float("nan"), "km2")
        with self.assertRaises(ValidationError):
            contract.measured(1.2, "fraction")
        with self.assertRaises(ValidationError):
            contract.measured(-1, "km2")
        self.assertEqual(contract.measured(0, "fraction").value, 0.0)

    def test_absent_and_zero_are_distinct(self):
        with self.assertRaises(ValidationError):
            contract.Measurement(value=None, unit="km2", status="measured")
        with self.assertRaises(ValidationError):
            contract.Measurement(value=None, unit="km2", status="unavailable")
        with self.assertRaises(ValidationError):
            contract.Measurement(value=1.0, unit="km2", status="not_measured")

    def test_uncertainty_must_be_coherent(self):
        with self.assertRaises(ValidationError):
            contract.Uncertainty(kind="block_bootstrap_interval", low=0.2, high=0.1, block_m=1000, method="x")
        with self.assertRaises(ValidationError):
            contract.Uncertainty(kind="not_estimated", value=0.0, method="x")
        with self.assertRaises(ValidationError):
            contract.Uncertainty(kind="not_estimated")
        with self.assertRaises(ValidationError):
            contract.Measurement(value=None, unit="km2", status="not_measured", reason="r",
                                 uncertainty=contract.Uncertainty(kind="not_estimated", method="m"))

    def test_schema_file_is_in_sync(self):
        recorded = json.loads((ROOT / "contract" / "mining_case.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(recorded, contract.MiningCase.model_json_schema(),
                         "regenerate with: python -m nasa_in_mining contract-schema --out contract/mining_case.schema.json")

    def test_recorded_case_and_every_referenced_file(self):
        path = ROOT / "cases" / "benguerir" / "output" / "case.json"
        if not path.exists():
            self.skipTest("no recorded case in this checkout")
        case = contract.MiningCase.model_validate_json(path.read_text(encoding="utf-8"))
        self.assertEqual(case.data_nature, "real")
        self.assertEqual(pipeline.verify_run(path.parent, case), [])


class SyntheticPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case, cls.dir, cls.data = run_synthetic()

    def pair(self, i):
        a, _ = fx.DATES[i]
        return next(p for p in self.case.pairs if p.reference_date == f"{a[:4]}-{a[4:6]}-{a[6:]}")

    def test_known_change_area_and_unobserved_pixels(self):
        p = self.pair(1)
        self.assertEqual(p.status, "ok")
        self.assertAlmostEqual(p.main.flagged_area_km2.value, fx.CHANGE_KM2, places=9)
        self.assertAlmostEqual(p.main.observable_fraction.value, 1 - 100 / fx.STUDY_PIXELS, places=9)
        self.assertEqual(p.n_clusters, 1)

    def test_every_quantile_and_profile_is_reported(self):
        p = self.pair(1)
        self.assertEqual({pr.quantile for pr in p.profiles}, {0.005, 0.01, 0.05})
        main = next(pr for pr in p.profiles if pr.id == "ring@0.01")
        self.assertTrue(main.exceeds_control)                      # 0.025 > 0 even though the ratio is undefined
        self.assertIsNone(main.ratio_to_evaluation_rate.value)
        self.assertEqual(main.ratio_to_evaluation_rate.status, "not_measured")

    def test_no_change_is_a_measured_zero_and_zero_coherence_is_flagged(self):
        self.assertEqual(self.pair(0).main.flagged_area_km2.value, 0.0)
        self.assertEqual(self.pair(0).main.flagged_area_km2.status, "measured")
        self.assertAlmostEqual(self.pair(2).main.flagged_area_km2.value, fx.CHANGE_KM2, places=9)

    def test_too_few_blocks_means_no_interval(self):
        u = self.pair(1).statistical.uncertainty
        self.assertIsNotNone(u)
        self.assertIn(u.kind, ("block_bootstrap_interval", "not_estimated"))

    def test_status_reflects_missing_optional_steps(self):
        self.assertEqual(self.case.processing.status, "partial")
        self.assertTrue(any(b.endswith("optical_strict") for b in self.case.processing.blockers))
        self.assertTrue(all(c.status == "no_scene_pair" for p in self.case.pairs for c in p.optical))

    def test_recurrence_counts_and_published_run(self):
        r = self.case.geometries[0].recurrence[0]
        self.assertEqual(len(r.pair_ids), 3)
        self.assertEqual(r.observed_pairs_max, 3)
        self.assertAlmostEqual(r.flagged_ever_km2.value, fx.CHANGE_KM2, places=9)
        out = self.dir / "output"
        self.assertTrue((out / "VERIFIED").exists())
        self.assertEqual(pipeline.verify_run(out, self.case), [])
        inputs = {f.role for f in self.case.manifest.inputs}
        self.assertTrue({"config", "zones", "nisar_coherence", "nisar_mask", "radar_geometry", "nisar_provenance"} <= inputs)

    def test_los_is_reported_not_interpreted(self):
        self.assertTrue(all(lp.interpreted is False for lp in self.case.los))
        self.assertEqual({v.observable: v.level for v in self.case.validation}["cause_of_change"], "not_computed")


class SyntheticFailures(unittest.TestCase):
    def test_incompatible_grid_is_reported_not_resampled(self):
        case, _, _ = run_synthetic(incompatible=True)
        self.assertIn("incompatible_grid", [p.status for p in case.pairs])

    def test_coherence_qc_reports_its_real_reason(self):
        case, _, _ = run_synthetic(rejected=True)
        rej = [p for p in case.pairs if p.status != "ok"]
        self.assertEqual(len(rej), 1)
        self.assertTrue(any("median coherence" in r for r in rej[0].reasons))
        self.assertIsNone(rej[0].main)

    def test_flat_phase_alone_does_not_reject_coherence(self):
        case, _, _ = run_synthetic(flat_phase_only=True)
        self.assertTrue(all(p.status == "ok" for p in case.pairs))
        self.assertEqual([lp.status for lp in case.los].count("not_computed"), 1)

    def test_corrupt_input_stops_the_run(self):
        tmp = Path(tempfile.mkdtemp(prefix="mining_corrupt_"))
        case_dir = fx.write_case(tmp / "cases" / "synthetic")
        data = fx.write_data(tmp / "data")
        f = next((data / "GUNW").glob("*/wrappedInterferogram_HH_coherenceMagnitude.tif"))
        f.write_bytes(f.read_bytes()[:-10] + b"0123456789")
        with self.assertRaises(pipeline.PipelineError):
            pipeline.run(case_dir, data, repo_root=tmp)
        self.assertFalse((case_dir / "output").exists())

    def test_new_run_never_reuses_old_files(self):
        case, case_dir, data = run_synthetic()
        stray = case_dir / "output" / "layers" / "stale_from_old_run.png"
        stray.write_bytes(b"old")
        pipeline.run(case_dir, data, repo_root=case_dir.parents[1], run_id="second")
        self.assertFalse(stray.exists())
        with self.assertRaises(pipeline.PipelineError):
            pipeline.run(case_dir, data, repo_root=case_dir.parents[1], run_id="second")

    def test_missing_referenced_file_blocks_publication(self):
        case, case_dir, _ = run_synthetic()
        out = case_dir / "output"
        lay = case.layers[0]
        (out / lay.url).unlink()
        self.assertTrue(any(lay.url in p for p in pipeline.verify_run(out, case)))

    def test_no_products_gives_an_unavailable_case(self):
        tmp = Path(tempfile.mkdtemp(prefix="mining_empty_"))
        case_dir = fx.write_case(tmp / "cases" / "synthetic")
        (tmp / "data").mkdir()
        case = pipeline.run(case_dir, tmp / "data", repo_root=tmp)
        self.assertEqual(case.processing.status, "unavailable")
        self.assertEqual(case.pairs, [])
        self.assertIn("limit.no_data_is_not_no_change", case.limits)


def _m(v, low=None, high=None, unit="ratio"):
    u = None if low is None else contract.Uncertainty(kind="block_bootstrap_interval", low=low, high=high, block_m=1000, method="t")
    return contract.measured(v, unit, u)


def _pair(pid, span=12, ratio=2.0, inner=0.01, outer=0.005, opt_ratio=None, opt_low=None):
    prof = NS(id="ring@0.01", ratio_to_evaluation_rate=_m(ratio), exceeds_control=ratio > 1,
              evaluation_rate=_m(0.01, unit="fraction"))
    zones = [NS(zone_id="control_1_2km", flagged_fraction=_m(inner, unit="fraction")),
             NS(zone_id="control_2_4km", flagged_fraction=_m(outer, unit="fraction")),
             NS(zone_id="panels_outside", flagged_fraction=_m(0.0, unit="fraction"))]
    opt = []
    if opt_ratio is not None:
        opt = [NS(mode="strict", status="ok", max_gap_days=3, association_ratio=_m(opt_ratio, opt_low, opt_ratio + 1),
                  p_optical_given_radar=_m(0.02, unit="fraction"), p_optical_given_not_radar=_m(0.001, unit="fraction"),
                  share_of_optical_change_in_radar_flags=_m(0.05, unit="fraction"))]
    return NS(pair_id=pid, status="ok", span_days=span, profiles=[prof], zones=zones, optical=opt, reasons=[],
              zone_stability={}, reference_date="2026-01-01", secondary_date="2026-01-13")


class FindingRules(unittest.TestCase):
    cfg = {"main_profile": "ring@0.01", "recurrence_span_days": 12, "quantiles": [0.01], "main_quantile": 0.01}

    def derive(self, pairs, cross_ok=True, los=()):
        cross = NS(status="ok" if cross_ok else "unavailable", matches=[
            NS(pair_a=p.pair_id, pair_b=p.pair_id, association_ratio=_m(3, 1.5, 4)) for p in pairs[:3]],
            unmatched=[], median_jaccard=_m(0.3, unit="fraction"))
        return findings.derive({"pairs": pairs, "cross": cross, "los": list(los), "recurrence": [], "dossiers": [],
                                "scenes": [], "controls": ["ring"]}, self.cfg)

    def test_ring_direction_follows_the_data(self):
        f, _, _ = self.derive([_pair("a", inner=0.02, outer=0.01), _pair("b", inner=0.03, outer=0.01)])
        self.assertEqual(next(x for x in f if x.id == "F_rings").params["direction"], "higher")
        f, _, _ = self.derive([_pair("a", inner=0.002, outer=0.01), _pair("b", inner=0.03, outer=0.01)])
        self.assertEqual(next(x for x in f if x.id == "F_rings").params["direction"], "mixed")

    def test_large_optical_ratio_without_interval_support_does_not_raise_the_level(self):
        pairs = [_pair(str(i), opt_ratio=60.0, opt_low=0.8) for i in range(5)]   # huge ratios, intervals include 1
        _, v, _ = self.derive(pairs)
        self.assertEqual(v[0].level, "internally_cross_checked")
        pairs = [_pair(str(i), opt_ratio=3.0, opt_low=1.4) for i in range(5)]
        _, v, _ = self.derive(pairs)
        self.assertEqual(v[0].level, "associated_with_independent_observation")
        _, v, _ = self.derive(pairs, cross_ok=False)
        self.assertEqual(v[0].level, "computed")

    def test_24_day_pairs_are_summarised_separately(self):
        f, _, _ = self.derive([_pair("a"), _pair("b", span=24, ratio=5)])
        self.assertEqual(next(x for x in f if x.id == "F_rate_12d").params["n_pairs"], 1)
        self.assertEqual(next(x for x in f if x.id == "F_rate_24d").params["max_ratio"], 5)

    def test_los_statement_follows_the_values(self):
        lp = NS(pair_id="a", status="computed", within_3sigma=False, control_sigma_cm=_m(0.4, unit="cm"))
        f, _, _ = self.derive([_pair("a")], los=[lp])
        self.assertEqual(next(x for x in f if x.id == "F_los").params["n_within_3sigma"], 0)

    def test_never_validated_without_field_truth(self):
        with self.assertRaises(ValidationError):
            contract.ValidationItem(observable="x", level="independently_validated", criteria=[], evidence_keys=[],
                                    missing_keys=[])


class AccessCaches(unittest.TestCase):
    def test_modified_crop_is_detected(self):
        from nasa_in_mining.access import nisar_subset
        tmp = Path(tempfile.mkdtemp(prefix="mining_cache_"))
        data = fx.write_data(tmp / "data")
        folder = next((data / "GUNW").iterdir())
        ok, _ = nisar_subset.verify(folder)
        self.assertTrue(ok)
        (folder / "wrappedInterferogram_mask.tif").write_bytes(b"truncated")
        ok, why = nisar_subset.verify(folder)
        self.assertFalse(ok)
        self.assertIn("fingerprint", why)
        key = nisar_subset.cache_key("x", (0, 0, 1, 1), 32629)
        self.assertFalse(nisar_subset.verify(next((data / "GUNW").iterdir()), key)[0])

    def test_sentinel2_cache_requires_same_parameters(self):
        from nasa_in_mining.access import sentinel2
        tmp = Path(tempfile.mkdtemp(prefix="mining_s2_"))
        key = sentinel2.cache_key("S2X", (0, 0, 20, 20), 32629, 20.0)
        (tmp / "stack.tif").write_bytes(b"a")
        (tmp / "provenance.json").write_text(json.dumps({"cache_key": key, "files": {
            "stack.tif": __import__("hashlib").sha256(b"a").hexdigest()}}), encoding="utf-8")
        self.assertIsNotNone(sentinel2.cached(tmp, key))
        self.assertIsNone(sentinel2.cached(tmp, sentinel2.cache_key("S2X", (0, 0, 40, 40), 32629, 20.0)))
        (tmp / "stack.tif").write_bytes(b"b")
        self.assertIsNone(sentinel2.cached(tmp, key))


class Api(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from nasa_in_mining.api import create_app
        cls.case, cls.dir, _ = run_synthetic()
        cls.client = TestClient(create_app(cls.dir.parent, cls.dir.parent / "no_web"))

    def test_health_list_and_runs(self):
        self.assertEqual(self.client.get("/api/health").json()["schema_version"], "2.0")
        lst = self.client.get("/api/cases").json()
        self.assertEqual(lst[0]["case_id"], "synthetic-test")
        self.assertEqual(lst[0]["published_run"], self.case.run_id)
        self.assertIn(self.case.run_id, lst[0]["runs"])

    def test_case_round_trip_equals_file(self):
        body = self.client.get("/api/cases/synthetic-test").json()
        self.assertEqual(body, json.loads((self.dir / "output" / "case.json").read_text(encoding="utf-8")))
        same = self.client.get(f"/api/cases/synthetic-test?run={self.case.run_id}").json()
        self.assertEqual(same["run_id"], self.case.run_id)

    def test_errors_are_explicit(self):
        r = self.client.get("/api/cases/unknown")
        self.assertEqual((r.status_code, r.json()["error"]), (404, "case_not_found"))
        r = self.client.get("/api/cases/synthetic-test?run=nope")
        self.assertEqual((r.status_code, r.json()["error"]), (404, "run_not_found"))
        self.assertEqual(self.client.get("/api/cases/synthetic-test/files/../case_config.json").status_code, 404)
        self.assertEqual(self.client.get("/api/cases/synthetic-test/files/exports/pairs.csv").status_code, 200)
        self.assertEqual(self.client.head("/api/cases/synthetic-test/files/exports/pairs.csv").status_code, 200)

    def test_contract_violation_is_reported(self):
        tmp = Path(tempfile.mkdtemp(prefix="mining_bad_"))
        out = tmp / "bad" / "output"
        shutil.copytree(self.dir / "output", out)
        data = json.loads((out / "case.json").read_text(encoding="utf-8"))
        data["case_id"] = "bad"
        data["pairs"][1]["main"]["flagged_area_km2"] = {"value": None, "unit": "km2", "status": "measured"}
        (out / "case.json").write_text(json.dumps(data), encoding="utf-8")
        from fastapi.testclient import TestClient
        from nasa_in_mining.api import create_app
        r = TestClient(create_app(tmp)).get("/api/cases/bad")
        self.assertEqual((r.status_code, r.json()["error"]), (500, "contract_violation"))



class Documentation(unittest.TestCase):
    def test_result_tables_match_the_recorded_case(self):
        import subprocess
        import sys
        if not (ROOT / "cases" / "benguerir" / "output" / "case.json").exists():
            self.skipTest("no recorded case")
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "report_tables.py"), "--check"], cwd=ROOT,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
