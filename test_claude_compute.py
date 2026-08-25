#!/usr/bin/env python3
"""Claude-compute leftover measures the farm; it does not lock posting."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from claude_compute import (
    CALIBRATION,
    PACKET_FIELDS,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    SUPERSEDES_BREADTH,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
    packet_ok,
)


class TestClaudeCompute(unittest.TestCase):
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
                "quarantine_present": True,
                "packet_present": True,
            }
        )
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("instrument failure", verdict["note"])

    def test_missing_paths_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "quarantine_present": False,
                "packet_present": False,
                "misses": ["ground/CLAUDE_COMPUTE.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_incomplete_phrases_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "quarantine_present": True,
                "packet_present": True,
                "found_phrases": ["compiler farm"],
                "packet_fields": ["spec"],
                "posting_open": True,
                "adjudicator_in_advance": True,
                "no_self_adjudicate": True,
                "opus5_bulk": True,
                "claude_does_not_decide": True,
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
                "quarantine_present": True,
                "packet_present": True,
                "found_phrases": list(REQUIRED_PHRASES),
                "packet_fields": list(PACKET_FIELDS),
                "posting_open": True,
                "adjudicator_in_advance": True,
                "no_self_adjudicate": True,
                "opus5_bulk": True,
                "claude_does_not_decide": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])
        self.assertIn("CANDIDATE", verdict["note"])

    def test_live_tree_measures_integrated(self):
        row = measure_root(ROOT)
        verdict = classify(row)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertEqual(row.get("slack_ts") or SLACK_TS, SLACK_TS)
        self.assertEqual(
            row.get("supersedes_breadth") or SUPERSEDES_BREADTH,
            SUPERSEDES_BREADTH,
        )

    def test_catalog_parses_farm(self):
        catalog_path = os.path.join(ROOT, "ground", "CLAUDE_COMPUTE.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["posting"], "OPEN")
        self.assertEqual(catalog["label"], "CLAUDE_INTERMEDIATE_UNTRUSTED")
        self.assertTrue(catalog["adjudicator_in_advance"])
        self.assertFalse(catalog["claude_self_adjudicate"])
        self.assertTrue(catalog["opus5_bulk_drafting"])
        self.assertFalse(catalog["claude_decides_correctness"])
        self.assertTrue(catalog["no_auth"])
        self.assertTrue(catalog["no_gate"])

    def test_claude_cannot_self_adjudicate(self):
        ok, note = packet_ok(
            {
                "label": "CLAUDE_INTERMEDIATE_UNTRUSTED",
                "spec": "x",
                "input_corpus": "y",
                "claimed_paths": ["p"],
                "acceptance_criteria": "z",
                "output_directory": "claude_compute/staging/x/",
                "adjudicator": "RIVET",
                "adjudicator_family": "non-claude",
                "canonical": False,
                "public_push": False,
            }
        )
        self.assertTrue(ok)
        self.assertEqual(note, "CANDIDATE")
        bad, why = packet_ok(
            {
                "label": "CLAUDE_INTERMEDIATE_UNTRUSTED",
                "spec": "x",
                "input_corpus": "y",
                "claimed_paths": ["p"],
                "acceptance_criteria": "z",
                "output_directory": "out",
                "adjudicator": "Claude",
            }
        )
        self.assertFalse(bad)
        self.assertIn("self-adjudicate", why)

    def test_search_space_and_calibration_named(self):
        self.assertIn("ground/CLAUDE_COMPUTE.md", SEARCH_SPACE)
        self.assertIn("claude_compute/PACKET.example.json", SEARCH_SPACE)
        self.assertIn("ground/EXECUTE.md", CALIBRATION)


if __name__ == "__main__":
    unittest.main()
