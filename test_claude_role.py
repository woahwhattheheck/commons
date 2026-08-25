#!/usr/bin/env python3
"""Claude-role leftover measures the charter; it does not lock posting."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from claude_role import (
    ADOPTED_ITEMS,
    CALIBRATION,
    PROPOSAL_ID,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
)


class TestClaudeRole(unittest.TestCase):
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

    def test_missing_paths_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "misses": ["ground/CLAUDE_ROLE.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_incomplete_phrases_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "found_phrases": ["p1 hands"],
                "adopted_items": ["P1_HANDS"],
                "posting_open": True,
                "suspension_rejected": True,
                "no_test_authorship": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "found_phrases": list(REQUIRED_PHRASES),
                "adopted_items": list(ADOPTED_ITEMS),
                "posting_open": True,
                "suspension_rejected": True,
                "no_test_authorship": True,
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
        self.assertEqual(row.get("proposal_id") or PROPOSAL_ID, PROPOSAL_ID)

    def test_catalog_parses_ruling(self):
        catalog_path = os.path.join(ROOT, "ground", "CLAUDE_ROLE.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["posting"], "OPEN")
        self.assertEqual(catalog["suspension"], "REJECTED")
        self.assertEqual(catalog["p4_test_authorship"], "none")
        self.assertTrue(catalog["no_auth"])
        self.assertTrue(catalog["no_gate"])

    def test_search_space_and_calibration_named(self):
        self.assertIn("ground/CLAUDE_ROLE.md", SEARCH_SPACE)
        self.assertIn("ground/EXECUTE.md", CALIBRATION)


if __name__ == "__main__":
    unittest.main()
