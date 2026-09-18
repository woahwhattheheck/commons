#!/usr/bin/env python3
"""Sitting remint leftover names already-landed leftovers and refuses a remint."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from sitting_remint import (
    ALREADY_LANDED,
    CALIBRATION,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
)


class TestSittingRemint(unittest.TestCase):
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
                "misses": ["ground/SITTING_REMINT.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_missing_named_leftover_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "landed_present": ["ground/CLAUDE_COMPUTE.md"],
                "landed_missing": ["ground/CASH_NOW.md"],
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
        self.assertEqual(row.get("slack_ts") or SLACK_TS, SLACK_TS)

    def test_catalog_parses_already_landed(self):
        catalog_path = os.path.join(ROOT, "ground", "SITTING_REMINT.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["posting"], "OPEN")
        self.assertTrue(catalog["no_auth"])
        self.assertTrue(catalog["no_gate"])
        self.assertIn("ground/CLAUDE_COMPUTE.md", catalog["already_landed"])
        self.assertIn("ground/CLAUDE_INTERMEDIATE.md", catalog["already_landed"])

    def test_search_space_and_calibration_named(self):
        self.assertIn("ground/SITTING_REMINT.md", SEARCH_SPACE)
        self.assertIn("ground/CLAUDE_COMPUTE.md", SEARCH_SPACE)
        self.assertIn("ground/CLAUDE_COMPUTE.md", CALIBRATION)
        self.assertIn("ground/EXECUTE.md", CALIBRATION)
        self.assertIn("ground/CASH_NOW.md", ALREADY_LANDED)
        self.assertIn("ground/JOJO_ASSIGN.md", ALREADY_LANDED)


if __name__ == "__main__":
    unittest.main()
