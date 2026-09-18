#!/usr/bin/env python3
"""Cursor-halt leftover names the until-further-notice 93% stop."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from cursor_halt import (
    ALREADY_LANDED,
    CALIBRATION,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    USAGE_PCT,
    classify,
    halt_state,
    load_catalog,
    measure_from_rows,
    measure_root,
)


class TestCursorHalt(unittest.TestCase):
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
                "misses": ["ground/CURSOR_HALT.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_missing_named_leftover_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "landed_present": ["ground/GROK_APP_ROUTE.md"],
                "landed_missing": ["host/grok_app_route.py"],
                "found_phrases": list(REQUIRED_PHRASES),
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("already-landed", verdict["note"])

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
                "halt": "HALT_ACTIVE",
                "usage_pct": USAGE_PCT,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])
        self.assertIn("HALT_ACTIVE", verdict["note"])
        self.assertEqual(verdict["halt"], "HALT_ACTIVE")

    def test_halt_active_until_bryce_lifts(self):
        self.assertEqual(halt_state({"until_notice": True, "usage_pct": 93}), "HALT_ACTIVE")
        self.assertEqual(
            halt_state(
                {
                    "until_notice": True,
                    "window_until": "2026-08-26T14:59:46Z",
                }
            ),
            "NOT_LANDED",
        )
        self.assertEqual(
            halt_state({"until_notice": True, "closed": True, "closed_by": "BRYCE"}),
            "HALT_LIFTED",
        )
        self.assertEqual(
            halt_state({"until_notice": True, "closed": True, "closed_by": "PEER"}),
            "NOT_LANDED",
        )
        self.assertEqual(halt_state({"until_notice": False}), "NOT_LANDED")

    def test_twenty_four_hour_remint_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
                "halt": "NOT_LANDED",
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("24-hour", verdict["note"])

    def test_live_tree_measures_integrated(self):
        row = measure_root(ROOT)
        verdict = classify(row)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertFalse(row["landed_missing"])
        self.assertEqual(row.get("slack_ts") or SLACK_TS, SLACK_TS)
        self.assertEqual(row["halt"], "HALT_ACTIVE")
        self.assertEqual(row["usage_pct"], USAGE_PCT)

    def test_catalog_parses_halt(self):
        catalog_path = os.path.join(ROOT, "ground", "CURSOR_HALT.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["usage_pct"], USAGE_PCT)
        self.assertTrue(catalog["until_notice"])
        self.assertEqual(catalog["window_until"], "")
        self.assertFalse(catalog["closed"])
        self.assertEqual(catalog["posting"], "OPEN")
        self.assertTrue(catalog["no_auth"])
        self.assertTrue(catalog["no_gate"])
        self.assertIn("ground/GROK_APP_ROUTE.md", catalog["already_landed"])
        self.assertEqual(halt_state(catalog), "HALT_ACTIVE")

    def test_search_space_and_calibration_named(self):
        normalized_search = [path.replace("\\", "/") for path in SEARCH_SPACE]
        normalized_calibration = [path.replace("\\", "/") for path in CALIBRATION]
        normalized_landed = [path.replace("\\", "/") for path in ALREADY_LANDED]
        self.assertIn("ground/CURSOR_HALT.md", normalized_search)
        self.assertIn("ground/GROK_APP_ROUTE.md", normalized_search)
        self.assertIn("ground/GROK_APP_ROUTE.md", normalized_calibration)
        self.assertIn("ground/EXECUTE.md", normalized_calibration)
        self.assertIn("host/grok_app_route.py", normalized_landed)
        self.assertIn("ground/SITTING_REMINT.md", normalized_landed)


if __name__ == "__main__":
    unittest.main()
