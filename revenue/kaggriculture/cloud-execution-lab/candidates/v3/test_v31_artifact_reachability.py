#!/usr/bin/env python3
"""Unit tests for check_v31_artifact_reachability.py; no canonical archive required."""
import json
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
                },
                "params": {
                    "lane_limit": 3,
                },
            }
        }
        files = {
            "main.py": b"from titan_runtime import run\n",
            "titan_runtime.py": (
                b"def run(cfg):\n"
                b"    limit = cfg.get('lane_limit', 3)\n"
                b"    if cfg.get('lane_flag'):\n"
                b"        from lane_mod import run_lane\n"
                b"        return run_lane() + limit\n"
                b"    return limit\n"
            ),
            "lane_mod.py": lane,
            "TITAN-CONFIG.json": b'{"lane_flag": false, "lane_limit": 3}',
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
            b"    return bool(cfg.get('lane_flag')) + cfg.get('lane_limit', 3)\n"
        )
        errors = validate_reachability(manifest, files, overlay)
        self.assertTrue(any("not import-reachable" in error for error in errors))

    def test_config_or_runtime_key_drift_fails(self):
        manifest, files, overlay = self.fixture()
        files["TITAN-CONFIG.json"] = b'{"lane_limit": 3}'
        files["titan_runtime.py"] = (
            b"from lane_mod import run_lane\n"
            b"def run(cfg):\n"
            b"    return run_lane() + cfg.get('lane_limit', 3)\n"
        )
        errors = validate_reachability(manifest, files, overlay)
        self.assertTrue(any("lane_flag: missing from TITAN-CONFIG.json" in error for error in errors))
        self.assertTrue(any("lane_flag: not referenced by executable code" in error for error in errors))

    def test_param_config_drift_fails(self):
        manifest, files, overlay = self.fixture()
        config = json.loads(files["TITAN-CONFIG.json"].decode("utf-8"))
        config["lane_limit"] = 4
        files["TITAN-CONFIG.json"] = json.dumps(config).encode("utf-8")
        errors = validate_reachability(manifest, files, overlay)
        self.assertTrue(any("lane_limit: config value 4 != manifest 3" in error for error in errors))

    def test_param_runtime_reference_is_required(self):
        manifest, files, overlay = self.fixture()
        files["titan_runtime.py"] = (
            b"from lane_mod import run_lane\n"
            b"def run(cfg):\n"
            b"    # lane_limit must not satisfy executable reachability\n"
            b"    if cfg.get('lane_flag'):\n"
            b"        return run_lane()\n"
            b"    return 0\n"
        )
        errors = validate_reachability(manifest, files, overlay)
        self.assertTrue(any("lane_limit: not referenced by executable code" in error for error in errors))

    def test_comment_docstring_and_inert_literal_do_not_satisfy_key_use(self):
        manifest, files, overlay = self.fixture()
        files["titan_runtime.py"] = (
            b"from lane_mod import run_lane\n"
            b"def run(cfg):\n"
            b"    '''lane_flag appears only in this docstring'''\n"
            b"    # lane_flag appears only in this comment\n"
            b"    note = 'lane_flag'\n"
            b"    return run_lane() + cfg.get('lane_limit', 3) + len(note) * 0\n"
        )
        errors = validate_reachability(manifest, files, overlay)
        self.assertTrue(any("lane_flag: not referenced by executable code" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
