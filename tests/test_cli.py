from tests import support as s

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


class CliTests(unittest.TestCase):
    def run_cli(self, *args, env=None):
        return subprocess.run([sys.executable, "-B", "-m", "nasa_in_mining", *args], capture_output=True,
                              text=True, encoding="utf-8", env=env or os.environ.copy(), timeout=45)

    def test_capabilities_needs_no_data(self):
        p = self.run_cli("capabilities")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("surface-change", json.loads(p.stdout)["recipes"])

    def test_empty_catalog_is_not_filled_with_mock_products(self):
        p = self.run_cli("catalog", "--data", str(s.ROOT / "missing_products"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout), [])

    def test_empty_analysis_has_explicit_status_and_exit_code(self):
        p = self.run_cli("analyze", "--data", str(s.ROOT / "missing_products"), "--recipe", "surface-change",
                         "--lat", str(s.LAT), "--lon", str(s.LON))
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertEqual(json.loads(p.stdout)["status"], "no_coverage")

    def test_actual_extracted_processing_from_a_new_process(self):
        data = s.make_products(s.ROOT / "cli_products")
        output = s.ROOT / "answer.json"
        p = self.run_cli("analyze", "--data", str(data), "--cache", str(s.ROOT / "cli_cache"),
                         "--recipe", "displacement", "--lat", str(s.LAT), "--lon", str(s.LON),
                         "--output", str(output))
        self.assertEqual(p.returncode, 0, p.stderr)
        out = json.loads(p.stdout)
        self.assertAlmostEqual(out["result"]["los_cm"], 2, delta=0.4)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), out)

    def test_defaults_are_offline_and_do_not_create_source_directories(self):
        env = os.environ.copy()
        for key in ("MINING_OFFLINE", "NISAR_OFFLINE", "MINING_DATA", "NISAR_DATA", "MINING_AUX", "NISAR_AUX"):
            env.pop(key, None)
        p = subprocess.run([sys.executable, "-B", "-c", "from nasa_in_mining import config; "
                            "assert config.OFFLINE; assert config.AUX_DIR.name == 'auxiliary'"],
                           env=env, capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr)
