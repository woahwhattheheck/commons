#!/usr/bin/env python3
"""JOJO-assign leftover measures the assignment protocol; it does not lock posting."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from jojo_assign import (
    ASSIGNMENT_FIELDS,
    CALIBRATION,
    IN_REPLY_TO,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
)


class TestJojoAssign(unittest.TestCase):
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
                "farm_present": True,
            }
        )
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("instrument failure", verdict["note"])

    def test_missing_paths_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "misses": ["ground/JOJO_ASSIGN.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_missing_farm_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "farm_present": False,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("farm dependency", verdict["note"])

    def test_incomplete_phrases_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "farm_present": True,
                "found_phrases": ["rule_ack"],
                "assignment_fields": ["spec"],
                "posting_open": True,
                "independent": True,
                "adjudicator_before": True,
                "non_claude_owned": True,
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
                "farm_present": True,
                "found_phrases": list(REQUIRED_PHRASES),
                "assignment_fields": list(ASSIGNMENT_FIELDS),
                "posting_open": True,
                "independent": True,
                "adjudicator_before": True,
                "non_claude_owned": True,
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
        self.assertEqual(row.get("slack_ts") or SLACK_TS, SLACK_TS)
        self.assertEqual(row.get("in_reply_to") or IN_REPLY_TO, IN_REPLY_TO)

    def test_catalog_parses_independence(self):
        catalog_path = os.path.join(ROOT, "ground", "JOJO_ASSIGN.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["kind"], "RULE_ACK")
        self.assertEqual(catalog["posting"], "OPEN")
        self.assertFalse(catalog["jojo_decisions_depend_on_claude_verdict"])
        self.assertTrue(catalog["adjudicator_before_assignment"])
        self.assertEqual(catalog["grok_recovery_owner"], "non-claude")
        self.assertTrue(catalog["no_auth"])
        self.assertTrue(catalog["no_gate"])

    def test_search_space_and_calibration_named(self):
        self.assertIn("ground/JOJO_ASSIGN.md", SEARCH_SPACE)
        self.assertIn("ground/CLAUDE_COMPUTE.md", SEARCH_SPACE)
        self.assertIn("ground/EXECUTE.md", CALIBRATION)


if __name__ == "__main__":
    unittest.main()
