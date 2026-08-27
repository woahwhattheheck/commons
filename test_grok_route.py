#!/usr/bin/env python3
"""24h grok.com route leftover names the window and refuses a Cursor lock."""

from __future__ import annotations

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from grok_route import (
    CALIBRATION,
    PREFER,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    WINDOW_HOURS,
    WINDOW_START,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
    window_state,
)


class TestGrokRoute(unittest.TestCase):
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
                "misses": ["ground/GROK_ROUTE.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_lock_framing_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "found_phrases": list(REQUIRED_PHRASES),
                "names_window": True,
                "names_not_a_lock": False,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("not a lock", verdict["note"].lower())

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "found_phrases": list(REQUIRED_PHRASES),
                "names_window": True,
                "names_not_a_lock": True,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_window_states(self):
        pending = window_state("2026-08-25T14:59:45Z")
        self.assertEqual(pending["state"], "PENDING")
        self.assertFalse(pending["locked"])
        active = window_state("2026-08-25T15:00:00Z")
        self.assertEqual(active["state"], "ACTIVE")
        self.assertEqual(active["prefer"], list(PREFER))
        self.assertFalse(active["locked"])
        expired = window_state("2026-08-26T14:59:46Z")
        self.assertEqual(expired["state"], "EXPIRED")
        self.assertFalse(expired["locked"])
        missing = window_state("")
        self.assertEqual(missing["state"], "UNMEASURED")
        self.assertIn("never 0", missing["note"].lower())
        invalid = window_state("not-a-clock")
        self.assertEqual(invalid["state"], "UNMEASURED")

    def test_live_tree_is_integrated(self):
        row = measure_root(ROOT, "2026-08-25T15:00:00Z")
        verdict = classify(row)
        self.assertTrue(row["calibration_ok"], row)
        self.assertEqual(set(row["calibration_hits"]), set(CALIBRATION))
        self.assertEqual(verdict["state"], "INTEGRATED", verdict)
        self.assertEqual(row["window"]["state"], "ACTIVE")
        self.assertFalse(row["window"]["locked"])
        catalog_path = os.path.join(ROOT, "ground", "GROK_ROUTE.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["window_start"], WINDOW_START)
        self.assertEqual(int(catalog["window_hours"]), WINDOW_HOURS)
        self.assertTrue(catalog["not_a_lock"])
        self.assertEqual(catalog["posting"], "OPEN")
        for rel in SEARCH_SPACE[:3]:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)


if __name__ == "__main__":
    unittest.main()
