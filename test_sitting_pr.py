#!/usr/bin/env python3
"""Sitting remint PR leftover names open remints and refuses a second land."""

from __future__ import annotations

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from sitting_pr import (
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


class TestSittingPr(unittest.TestCase):
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
                "misses": ["ground/SITTING_PR.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_claiming_2207_integrated_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "sitting_remints": [{"number": "2207", "land_state": "INTEGRATED"}],
                "names_2207_superseded": False,
                "claims_2207_integrated": True,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("SUPERSEDED", verdict["note"])

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "sitting_remints": [{"number": "2207", "land_state": "SUPERSEDED"}],
                "names_2207_superseded": True,
                "claims_2207_integrated": False,
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
        self.assertTrue(row["names_2207_superseded"])
        self.assertFalse(row["claims_2207_integrated"])
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertEqual(SLACK_TS, "1787645172.017469")
        self.assertEqual(len(CALIBRATION), 3)
        self.assertGreaterEqual(len(SEARCH_SPACE), 8)
        with open(os.path.join(ROOT, "ground", "SITTING_PR.json"), encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["sitting_remints"][0]["number"], "2207")
        self.assertEqual(catalog["sitting_remints"][0]["land_state"], "SUPERSEDED")
        self.assertEqual(classify(row)["state"], "INTEGRATED")


if __name__ == "__main__":
    unittest.main()
