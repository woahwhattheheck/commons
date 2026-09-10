from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import materialize_capital_firewall as firewall
import materialize_weed_off as weed_off


class MaterializerTests(unittest.TestCase):
    def test_weed_off_is_one_exact_substitution(self):
        fixture = "prefix\n" + weed_off.OLD + "suffix\n"
        result = weed_off.patch_text(fixture)
        self.assertNotIn(weed_off.OLD, result)
        self.assertEqual(result.count(weed_off.NEW), 1)

    def test_weed_off_refuses_ambiguous_anchor(self):
        with self.assertRaises(ValueError):
            weed_off.patch_text(weed_off.OLD * 2)

    def test_firewall_patches_are_single_anchor(self):
        spatial = firewall.SPATIAL_INIT_OLD + firewall.SPATIAL_COMMIT_OLD
        spatial = firewall.replace_once(spatial, firewall.SPATIAL_INIT_OLD,
                                        firewall.SPATIAL_INIT_NEW, "init")
        spatial = firewall.replace_once(spatial, firewall.SPATIAL_COMMIT_OLD,
                                        firewall.SPATIAL_COMMIT_NEW, "commit")
        self.assertIn("weed_continuation_sites=set()", spatial)
        self.assertIn("weed_continuation_sites.add(origin)", spatial)
        runtime = firewall.RUNTIME_METHOD_ANCHOR + firewall.RUNTIME_CALL_OLD
        runtime = firewall.replace_once(runtime, firewall.RUNTIME_METHOD_ANCHOR,
                                        firewall.RUNTIME_METHOD + firewall.RUNTIME_METHOD_ANCHOR,
                                        "method")
        runtime = firewall.replace_once(runtime, firewall.RUNTIME_CALL_OLD,
                                        firewall.RUNTIME_CALL_NEW, "call")
        self.assertIn("_weed_capital_firewall_selected", runtime)
        self.assertIn("stage = 'weed_capital_firewall'", runtime)

    def test_firewall_refuses_missing_anchor(self):
        with self.assertRaises(ValueError):
            firewall.replace_once("", "missing", "new", "test")


if __name__ == "__main__":
    unittest.main()
