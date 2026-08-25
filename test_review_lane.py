#!/usr/bin/env python3
"""Review-lane leftover names PR #3 CANDIDATE and refuses a false official-main land."""

from __future__ import annotations

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from review_lane import (
    ALREADY_LANDED,
    CALIBRATION,
    CANDIDATE_SHA,
    OFFICIAL_MAIN,
    PR_NUMBER,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
)


class TestReviewLane(unittest.TestCase):
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
                "misses": ["ground/REVIEW_LANE.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_claiming_pr3_integrated_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "candidates": [{"number": "3", "land_state": "FOREIGN_INTEGRATED"}],
                "names_pr3_candidate": False,
                "claims_pr3_integrated": True,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("CANDIDATE", verdict["note"])

    def test_claiming_receipt_on_official_main_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "names_pr3_candidate": True,
                "claims_receipt_on_official_main": True,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("ABSENT", verdict["note"])

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "candidates": [
                    {
                        "number": PR_NUMBER,
                        "land_state": "CANDIDATE",
                        "candidate_sha": CANDIDATE_SHA,
                        "official_main": OFFICIAL_MAIN,
                        "receipt_on_official_main": "ABSENT",
                    }
                ],
                "names_pr3_candidate": True,
                "claims_pr3_integrated": False,
                "claims_receipt_on_official_main": False,
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
        self.assertTrue(row["names_pr3_candidate"])
        self.assertFalse(row["claims_pr3_integrated"])
        self.assertFalse(row["claims_receipt_on_official_main"])
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertEqual(SLACK_TS, "1787647408.984179")
        self.assertEqual(len(CALIBRATION), 3)
        self.assertGreaterEqual(len(SEARCH_SPACE), 8)
        with open(os.path.join(ROOT, "ground", "REVIEW_LANE.json"), encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["candidates"][0]["number"], "3")
        self.assertEqual(catalog["candidates"][0]["land_state"], "CANDIDATE")
        self.assertEqual(catalog["candidates"][0]["receipt_on_official_main"], "ABSENT")
        self.assertEqual(catalog["candidates"][0]["candidate_sha"], CANDIDATE_SHA)
        self.assertEqual(classify(row)["state"], "INTEGRATED")


if __name__ == "__main__":
    unittest.main()
