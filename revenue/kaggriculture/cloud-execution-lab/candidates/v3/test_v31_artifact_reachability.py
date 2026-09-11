#!/usr/bin/env python3
"""Unit tests for check_v31_artifact_reachability.py; no canonical archive required."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from check_v31_artifact_reachability import validate_reachability  # noqa: E402


class ArtifactReachabilityTests(unittest.TestCase):
    def fixture(self):
        lane = b"def run_lane():\n    return 1\n"
        manifest = {
            "keys": {
                "lane_flag": {
                    "default": False,
                    "module": "lane_mod.py",
                }
            }
        }
        files = {
            "main.py": b"from titan_runtime import run\n",
            "titan_runtime.py": (
                b"def run(cfg):\n"
                b"    if cfg.get('lane_flag'):\n"
                b"        from lane_mod import run_lane\n"
                b"        return run_lane()\n"
                b"    return 0\n"
            ),
            "lane_mod.py": lane,
            "TITAN-CONFIG.json": b'{"lane_flag": false}',
        }
        overlay = {"lane_mod.py": lane}
        return manifest, files, overlay

    def test_valid_contract_passes(self):
        manifest, files, overlay = self.fixture()
        self.assertEqual([], validate_reachability(manifest, files, overlay))

    def test_missing_packed_module_fails(self):
        manifest, files, overlay = self.fixture()
        del files["lane_mod.py"]
        errors = validate_reachability(manifest, files, overlay)
        self.assertTrue(any("missing from built package" in error for error in errors))

    def test_overlay_byte_drift_fails(self):
        manifest, files, overlay = self.fixture()
        files["lane_mod.py"] = b"def run_lane():\n    return 2\n"
        errors = validate_reachability(manifest, files, overlay)
        self.assertTrue(any("differs from overlay source" in error for error in errors))

    def test_unreachable_module_fails(self):
        manifest, files, overlay = self.fixture()
        files["titan_runtime.py"] = (
            b"def run(cfg):\n"
            b"    return bool(cfg.get('lane_flag'))\n"
        )
        errors = validate_reachability(manifest, files, overlay)
        self.assertTrue(any("not import-reachable" in error for error in errors))

    def test_config_or_runtime_key_drift_fails(self):
        manifest, files, overlay = self.fixture()
        files["TITAN-CONFIG.json"] = b"{}"
        files["titan_runtime.py"] = b"from lane_mod import run_lane\ndef run(cfg):\n    return run_lane()\n"
        errors = validate_reachability(manifest, files, overlay)
        self.assertTrue(any("missing from TITAN-CONFIG.json" in error for error in errors))
        self.assertTrue(any("not referenced by code reachable" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
