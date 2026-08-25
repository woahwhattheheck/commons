#!/usr/bin/env python3
"""H-002 leftover names filesystem discovery and refuses a Slack first-clean land."""

from __future__ import annotations

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from h002 import (
    ALREADY_LANDED,
    CALIBRATION,
    DISCOVERY_SURFACES,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    TOKEN_RECEIPT,
    XHIGH_LANES,
    classify,
    classify_discovery,
    load_catalog,
    measure_from_rows,
    measure_root,
)


class TestH002(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_failed_calibration_is_instrument_failure(self):
        verdict = classify(
            {
                "measured": True,
                "calibration_ok": False,
                "calibration_hits": [],
                "card_present": True,
                "catalog_present": True,
            }
        )
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("instrument failure", verdict["note"])
        self.assertIn("never 0", verdict["note"].lower())

    def test_missing_paths_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "misses": ["ground/H002.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_compat_gate_claim_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "names_four_surfaces": True,
                "discovery_gated_by_compat": True,
                "disabled_means_discover": True,
                "names_token_receipt": True,
                "names_xhigh_lanes": True,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("merge", verdict["note"])

    def test_restore_registry_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "names_four_surfaces": True,
                "disabled_means_discover": True,
                "restore_registry": True,
                "names_token_receipt": True,
                "names_xhigh_lanes": True,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("do not restore", verdict["note"].lower())

    def test_patch_upstream_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "names_four_surfaces": True,
                "disabled_means_discover": True,
                "patch_upstream": True,
                "names_token_receipt": True,
                "names_xhigh_lanes": True,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("do not patch", verdict["note"].lower())

    def test_inspect_false_enabled_is_not_a_zero(self):
        verdict = classify_discovery(
            {
                "measured": True,
                "finder": "ok",
                "surface": "~/.claude/plugins/installed_plugins.json",
                "present": True,
                "disabled": True,
                "inspect_enabled": True,
            }
        )
        self.assertEqual(verdict["state"], "INSPECT_FALSE_ENABLED")
        self.assertIn("never 0", verdict["note"].lower())

    def test_failed_finder_is_not_zero(self):
        verdict = classify_discovery(
            {
                "measured": True,
                "finder": "failed",
                "surface": "marketplace metadata",
            }
        )
        self.assertEqual(verdict["state"], "FINDER-FAILED")
        self.assertIn("never 0", verdict["note"].lower())

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "names_four_surfaces": True,
                "disabled_means_discover": True,
                "names_token_receipt": True,
                "names_xhigh_lanes": True,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_live_tree_has_the_leftover(self):
        row = measure_root(ROOT)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(row["landed_missing"], [])
        self.assertTrue(row["names_four_surfaces"])
        self.assertFalse(row["discovery_gated_by_compat"])
        self.assertTrue(row["disabled_means_discover"])
        self.assertFalse(row["restore_registry"])
        self.assertFalse(row["patch_upstream"])
        self.assertTrue(row["names_token_receipt"])
        self.assertTrue(row["names_xhigh_lanes"])
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertEqual(SLACK_TS, "1787647999.742959")
        self.assertEqual(len(CALIBRATION), 3)
        self.assertGreaterEqual(len(SEARCH_SPACE), 8)
        self.assertEqual(len(DISCOVERY_SURFACES), 4)
        self.assertEqual(TOKEN_RECEIPT["calls"], 32)
        self.assertEqual(len(XHIGH_LANES), 3)
        with open(os.path.join(ROOT, "ground", "H002.json"), encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["disabled_means"], "discover-but-don't-load")
        self.assertFalse(catalog["discovery_gated_by_compat"])
        self.assertEqual(catalog["patch_upstream"], "DO_NOT_PATCH_YET")
        self.assertEqual(classify(row)["state"], "INTEGRATED")


if __name__ == "__main__":
    unittest.main()
