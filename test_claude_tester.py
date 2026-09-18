#!/usr/bin/env python3
"""Claude-tester leftover measures; it does not assign Claude a tester role."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from claude_tester import (
    CALIBRATION,
    LEDGER_PHRASES,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
)


class TestClaudeTester(unittest.TestCase):
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
                "ledger_present": True,
            }
        )
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("instrument failure", verdict["note"])

    def test_missing_paths_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "ledger_present": False,
                "misses": ["ground/CLAUDE_TESTER.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_incomplete_phrases_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "ledger_present": True,
                "found_phrases": ["stop using claude"],
                "found_ledger_phrases": [],
                "allowed_verifiers": ["Codex"],
                "preserve_claude_artifacts": True,
                "xyz_required": True,
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "ledger_present": True,
                "found_phrases": list(REQUIRED_PHRASES),
                "found_ledger_phrases": list(LEDGER_PHRASES),
                "allowed_verifiers": [
                    "deterministic local checks",
                    "GitHub Actions",
                    "Codex",
                    "Grok / direct xAI",
                    "Codex / Grok Build",
                ],
                "preserve_claude_artifacts": True,
                "xyz_required": True,
                "calibration_ok": True,
                "calibration_hits": list(CALIBRATION),
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_live_tree_matches_the_report(self):
        catalog_path = os.path.join(ROOT, "ground", "CLAUDE_TESTER.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertTrue(catalog["preserve_claude_artifacts"])
        self.assertTrue(catalog["xyz_required"])
        self.assertGreaterEqual(len(catalog["allowed_verifiers"]), 4)
        row = measure_root(ROOT)
        self.assertTrue(row["calibration_ok"], "known-present calibration must hit EXECUTE + Action Pad directive")
        self.assertEqual(sorted(row["calibration_hits"]), sorted(CALIBRATION))
        self.assertEqual(row["search_space"], list(SEARCH_SPACE))
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        self.assertIn("xyz", row["found_phrases"])
        self.assertIn("claude_tester", row["found_ledger_phrases"])


if __name__ == "__main__":
    unittest.main()
