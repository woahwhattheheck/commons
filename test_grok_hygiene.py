#!/usr/bin/env python3
"""Grok-hygiene leftover names the Claude plugin leak and keeps Opus enabled."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "host"))

from grok_hygiene import (
    ALREADY_LANDED,
    CALIBRATION,
    GATE_PATH,
    LEAK_PLUGINS,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
)


class TestGrokHygiene(unittest.TestCase):
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
                "misses": ["ground/GROK_HYGIENE.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_disable_claude_plugins_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "disables_claude_plugins": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("do not disable", verdict["note"].lower())

    def test_mutate_home_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "mutates_home": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("preserve evidence", verdict["note"].lower())

    def test_wrong_leak_set_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "leak_plugins": ["frontend-design"],
                "keep_claude_plugins": True,
                "fail_closed": True,
                "cursor_clean": True,
                "untrusted_candidate": True,
                "diligence_not_build": True,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "closes_door": False,
                "disables_claude_plugins": False,
                "mutates_home": False,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("frontend-design", verdict["note"])

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "leak_plugins": list(LEAK_PLUGINS),
                "keep_claude_plugins": True,
                "fail_closed": True,
                "cursor_clean": True,
                "untrusted_candidate": True,
                "diligence_not_build": True,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "closes_door": False,
                "disables_claude_plugins": False,
                "mutates_home": False,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_live_tree_measures_integrated(self):
        row = measure_root(ROOT)
        verdict = classify(row)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertFalse(row["landed_missing"])
        self.assertEqual(list(row.get("leak_plugins") or []), list(LEAK_PLUGINS))
        self.assertEqual(row.get("slack_ts") or SLACK_TS, SLACK_TS)

    def test_catalog_parses(self):
        catalog_path = os.path.join(ROOT, "ground", "GROK_HYGIENE.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["posting"], "OPEN")
        self.assertTrue(catalog["no_auth"])
        self.assertTrue(catalog["no_gate"])
        self.assertTrue(catalog["keep_claude_plugins"])
        self.assertEqual(catalog["direct_grok"], "FAIL_CLOSED")
        self.assertEqual(catalog["cursor_surface"], "CLEAN_LANE")
        self.assertEqual(catalog["claude_compute"], "UNTRUSTED_CANDIDATE")
        self.assertEqual(catalog["hygiene"], "DILIGENCE_NOT_BUILD")
        self.assertEqual(catalog["leak_plugins"], list(LEAK_PLUGINS))
        self.assertEqual(catalog["gate_path"], GATE_PATH)
        self.assertFalse(catalog["mutate_claude"])
        self.assertFalse(catalog["mutate_grok"])
        self.assertFalse(catalog["delete_sessions"])
        self.assertIn("ground/GROK_HARNESS.md", catalog["already_landed"])

    def test_search_space_and_calibration_named(self):
        self.assertIn("ground/GROK_HYGIENE.md", SEARCH_SPACE)
        self.assertIn("ground/GROK_HARNESS.md", SEARCH_SPACE)
        self.assertIn("ground/GROK_HARNESS.md", CALIBRATION)
        self.assertIn("ground/EXECUTE.md", CALIBRATION)
        self.assertIn("ground/MEMORY_SHIP.md", ALREADY_LANDED)
        self.assertEqual(LEAK_PLUGINS, (
            "frontend-design",
            "mcp-server-dev",
            "mcp-tunnels",
        ))


if __name__ == "__main__":
    unittest.main()
