"""Focused fail-closed checks for make_submission.py."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("make_submission.py")
FAKE_BUILD = """\
def package_files(canon):
    with open(canon, \"rb\") as handle:
        return {\"TITAN-CONFIG.json\": handle.read()}


def build_bytes(files):
    return files[\"TITAN-CONFIG.json\"]
"""
BASE_CONFIG = {
    "r03_full_router": False,
    "r04_sale_window": False,
    "r04_sale_horizon": 8,
    "r01_shop_router": False,
    "r02_route_bank": False,
}


class MakeSubmissionFailClosedTest(unittest.TestCase):
    def run_builder(self, config, *extra, optimize=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "build_v3.py").write_text(FAKE_BUILD, encoding="utf-8")
            canon = root / "canonical.json"
            canon.write_text(json.dumps(config), encoding="utf-8")
            out = root / "submission.tar.gz"
            cmd = [sys.executable]
            if optimize:
                cmd.append("-O")
            cmd.extend([str(SCRIPT), str(root), str(canon), str(out), *map(str, extra)])
            proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
            output = out.read_bytes() if out.exists() else None
            return proc, output

    def test_source_mode_precondition_fails_normally(self):
        config = dict(BASE_CONFIG, r04_sale_window=True)
        proc, output = self.run_builder(config)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIsNone(output)
        self.assertIn("expected source package r04_sale_window=false", proc.stderr + proc.stdout)

    def test_source_mode_precondition_survives_python_optimize(self):
        config = dict(BASE_CONFIG, r04_sale_window=True)
        proc, output = self.run_builder(config, optimize=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIsNone(output)
        self.assertIn("expected source package r04_sale_window=false", proc.stderr + proc.stdout)

    def test_invalid_horizons_fail_before_build(self):
        for horizon in (0, -1):
            with self.subTest(horizon=horizon):
                proc, output = self.run_builder(BASE_CONFIG, horizon)
                self.assertNotEqual(proc.returncode, 0)
                self.assertIsNone(output)
                self.assertIn("sale horizon must be at least 1", proc.stderr + proc.stdout)

    def test_valid_default_horizon_changes_only_sale_window(self):
        proc, output = self.run_builder(BASE_CONFIG)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        result = json.loads(output.decode("utf-8"))
        expected = dict(BASE_CONFIG, r04_sale_window=True)
        self.assertEqual(result, expected)

    def test_valid_explicit_horizon_is_applied(self):
        proc, output = self.run_builder(BASE_CONFIG, 12)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        result = json.loads(output.decode("utf-8"))
        expected = dict(BASE_CONFIG, r04_sale_window=True, r04_sale_horizon=12)
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
