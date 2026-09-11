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
                b"    if cfg.get('lane_flag'):\n"
                b"        from lane_mod import run_lane\n"
                b"        return run_lane()\n"
                b"    return cfg.get('lane_limit', 0)\n"
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
            b"    return bool(cfg.get('lane_flag')) + cfg.get('lane_limit', 0)\n"
        )
        errors = validate_reachability(manifest, files, overlay)
        self.assertTrue(any("not import-reachable" in error for error in errors))

    def test_config_or_runtime_key_drift_fails(self):
        manifest, files, overlay = self.fixture()
        files["TITAN-CONFIG.json"] = b"{}"
        files["titan_runtime.py"] = b"from lane_mod import run_lane\ndef run(cfg):\n    return run_lane()\n"
        errors = validate_reachability(manifest, files, overlay)
        self.assertTrue(any("lane_flag: missing from TITAN-CONFIG.json" in error for error in errors))
        self.assertTrue(any("lane_limit: missing from TITAN-CONFIG.json" in error for error in errors))
        self.assertTrue(any("lane_flag: not referenced by executable code" in error for error in errors))
        self.assertTrue(any("lane_limit: not referenced by executable code" in error for error in errors))

    def test_manifest_param_default_drift_fails(self):
        manifest, files, overlay = self.fixture()
        files["TITAN-CONFIG.json"] = b'{"lane_flag": false, "lane_limit": 4}'
        errors = validate_reachability(manifest, files, overlay)
        self.assertTrue(any("lane_limit: config default 4 != manifest 3" in error for error in errors))

    def test_manifest_param_type_drift_fails(self):
        manifest, files, overlay = self.fixture()
        manifest["keys"]["params"]["lane_limit"] = True
        files["TITAN-CONFIG.json"] = b'{"lane_flag": false, "lane_limit": 1}'
        errors = validate_reachability(manifest, files, overlay)
        self.assertTrue(any("lane_limit: config default 1 != manifest True" in error for error in errors))

    def test_param_comment_docstring_and_dead_string_do_not_count_as_use(self):
        manifest, files, overlay = self.fixture()
        files["titan_runtime.py"] = (
            b"from lane_mod import run_lane\n"
            b"def run(cfg):\n"
            b"    # lane_limit must not satisfy runtime reachability\n"
            b"    marker = 'lane_limit'\n"
            b"    if cfg.get('lane_flag'):\n"
            b"        return run_lane()\n"
            b"    return marker\n"
        )
        errors = validate_reachability(manifest, files, overlay)
        self.assertTrue(any("lane_limit: not referenced by executable code" in error for error in errors))

    def test_lane_comment_docstring_and_dead_string_do_not_count_as_use(self):
        manifest, files, overlay = self.fixture()
        files["titan_runtime.py"] = (
            b"from lane_mod import run_lane\n"
            b"def run(cfg):\n"
            b"    '''lane_flag'''\n"
            b"    # lane_flag must not satisfy runtime reachability\n"
            b"    marker = 'lane_flag'\n"
            b"    return run_lane() + cfg.get('lane_limit', 0)\n"
        )
        errors = validate_reachability(manifest, files, overlay)
        self.assertTrue(any("lane_flag: not referenced by executable code" in error for error in errors))

    def test_attribute_reference_counts_as_semantic_use(self):
        manifest, files, overlay = self.fixture()
        files["titan_runtime.py"] = (
            b"from lane_mod import run_lane\n"
            b"def run(self):\n"
            b"    if self.features.lane_flag:\n"
            b"        return run_lane()\n"
            b"    return self.features.lane_limit\n"
        )
        self.assertEqual([], validate_reachability(manifest, files, overlay))


if __name__ == "__main__":
    unittest.main()
