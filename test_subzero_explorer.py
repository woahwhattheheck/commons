#!/usr/bin/env python3
"""Subzero Artifact Explorer leftover verifies hashes and refuses sold runtime."""

from __future__ import annotations

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from subzero_explorer import (
    ALREADY_LANDED,
    CALIBRATION,
    EXPECTED_EXCERPTS,
    HANDOFF_ID,
    LDA_BLOCK,
    LDA_SHA,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
)


class TestSubzeroExplorer(unittest.TestCase):
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
                "door_present": True,
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
                "door_present": False,
                "misses": ["ground/SUBZERO_EXPLORER.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_sold_host_training_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "door_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "excerpt_count": EXPECTED_EXCERPTS,
                "hash_match_count": EXPECTED_EXCERPTS,
                "runtime_sold": False,
                "host_training_sold": True,
                "titan_mutation_sold": False,
                "lda_blocked": True,
                "copy_private_lda": False,
                "structural_only": True,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
                "titan": "NOT_WRITTEN",
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("host training", verdict["note"].lower())

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "door_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "excerpt_count": EXPECTED_EXCERPTS,
                "hash_match_count": EXPECTED_EXCERPTS,
                "runtime_sold": False,
                "host_training_sold": False,
                "titan_mutation_sold": False,
                "lda_blocked": True,
                "copy_private_lda": False,
                "structural_only": True,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
                "titan": "NOT_WRITTEN",
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
        self.assertEqual(row["excerpt_count"], EXPECTED_EXCERPTS)
        self.assertEqual(row["hash_match_count"], EXPECTED_EXCERPTS)
        self.assertTrue(row["structural_only"])
        self.assertTrue(row["lda_blocked"])
        self.assertFalse(row["host_training_sold"])
        self.assertFalse(row["runtime_sold"])
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertEqual(SLACK_TS, "1787646413.997539")
        self.assertEqual(HANDOFF_ID, "jojo-model-work-profitability-bridge-20260825-01")
        self.assertEqual(LDA_SHA, "fb0b0b2f59f8ca81741371b6ddd8036b164e77e8")
        self.assertEqual(LDA_BLOCK, "BLOCKED_ON_PUBLISHED_WIDE_RECEIVER_RESULT")
        self.assertEqual(len(CALIBRATION), 4)
        self.assertGreaterEqual(len(SEARCH_SPACE), 8)
        with open(os.path.join(ROOT, "ground", "SUBZERO_EXPLORER.json"), encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["label"], "STRUCTURAL_ONLY")
        self.assertEqual(catalog["host_training"], "NOT_SOLD")
        self.assertEqual(catalog["lda_state"], LDA_BLOCK)
        self.assertEqual(catalog["expected_excerpts"], EXPECTED_EXCERPTS)
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        self.assertGreaterEqual(row["archetypes"]["fabricators"], 53)
        self.assertGreaterEqual(row["archetypes"]["tests"], 32)


if __name__ == "__main__":
    unittest.main()
