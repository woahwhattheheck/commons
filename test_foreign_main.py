#!/usr/bin/env python3
"""Foreign-main leftover measures a Slack SHIP_RECEIPT against official main."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from foreign_main import (
    CALIBRATION,
    CLAIMED_MAIN,
    DEFAULT_BLOBS,
    DEFAULT_CARD,
    DEFAULT_CATALOG,
    JOJO_ID,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    blob_matches,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
    receipt_path,
)


class TestForeignMain(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])
        self.assertEqual(row["z"], "FINDER-FAILED")

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
                "misses": [DEFAULT_CARD],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_blob_mismatch_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "found_phrases": list(REQUIRED_PHRASES),
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
                "claimed_count": 3,
                "matched_count": 2,
                "official_main": CLAIMED_MAIN,
                "claimed_main": CLAIMED_MAIN,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("independently matched", verdict["note"])

    def test_copied_source_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "found_phrases": list(REQUIRED_PHRASES),
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "copied_source": True,
                "calibration_ok": True,
                "claimed_count": 3,
                "matched_count": 3,
                "official_main": CLAIMED_MAIN,
                "claimed_main": CLAIMED_MAIN,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_leftover_is_integrated_while_commons_receipt_missing(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "receipt_present": False,
                "source_id": JOJO_ID,
                "found_phrases": list(REQUIRED_PHRASES),
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
                "claimed_count": 3,
                "matched_count": 3,
                "official_main": CLAIMED_MAIN,
                "claimed_main": CLAIMED_MAIN,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertEqual(verdict["foreign_repo_state"], "FOREIGN_INTEGRATED")
        self.assertEqual(verdict["commons_receipt_state"], "CARRIER_ONLY")
        self.assertIn("still not the file", verdict["note"])

    def test_default_blobs_match(self):
        counts = blob_matches(list(DEFAULT_BLOBS))
        self.assertEqual(counts["claimed_count"], 3)
        self.assertEqual(counts["matched_count"], 3)
        self.assertEqual(counts["unverified_count"], 0)

    def test_receipt_path_and_catalog(self):
        self.assertEqual(receipt_path(JOJO_ID), os.path.join("p", JOJO_ID + ".md"))
        parsed = load_catalog("{")
        self.assertEqual(parsed["error"], "catalog is not JSON")
        live = load_catalog(
            '{"source_id":"%s","claimed_main":"%s","live_measure":{"official_main":"%s"},"posting":"OPEN"}'
            % (JOJO_ID, CLAIMED_MAIN, CLAIMED_MAIN)
        )
        self.assertEqual(live["source_id"], JOJO_ID)
        self.assertEqual(live["official_main"], CLAIMED_MAIN)

    def test_live_tree_is_integrated(self):
        row = measure_root(ROOT)
        verdict = classify(row)
        self.assertTrue(row["calibration_ok"], row.get("calibration_hits"))
        self.assertEqual(set(row["calibration_hits"]), set(CALIBRATION))
        self.assertEqual(row["slack_ts"], SLACK_TS)
        self.assertFalse(row["receipt_present"])
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertEqual(verdict["commons_receipt_state"], "CARRIER_ONLY")
        for rel in SEARCH_SPACE[:3]:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)
        self.assertTrue(os.path.isfile(os.path.join(ROOT, DEFAULT_CATALOG)))


if __name__ == "__main__":
    unittest.main()
