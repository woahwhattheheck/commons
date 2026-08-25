#!/usr/bin/env python3
"""Slack SHIP_RECEIPT leftover: source bytes are not the receipt file."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from slack_receipt import (
    DEFAULT_ID,
    DEFAULT_PATHS,
    SLACK_TS,
    classify,
    load_catalog,
    measure_root,
    present_paths,
    receipt_path,
)


class TestSlackReceipt(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_missing_sources_and_receipt_stay_not_landed(self):
        verdict = classify(
            {
                "measured": True,
                "source_id": DEFAULT_ID,
                "source_paths": list(DEFAULT_PATHS),
                "present_paths": [],
                "receipt_present": False,
            }
        )
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn(DEFAULT_ID, verdict["note"])

    def test_sources_without_receipt_are_carrier_only(self):
        verdict = classify(
            {
                "measured": True,
                "source_id": DEFAULT_ID,
                "source_paths": list(DEFAULT_PATHS),
                "present_paths": list(DEFAULT_PATHS),
                "receipt_present": False,
            }
        )
        self.assertEqual(verdict["state"], "CARRIER_ONLY")
        self.assertIn("mail", verdict["note"])
        self.assertIn("Do not remint", verdict["note"])

    def test_receipt_without_all_sources_is_candidate(self):
        verdict = classify(
            {
                "measured": True,
                "source_id": DEFAULT_ID,
                "source_paths": list(DEFAULT_PATHS),
                "present_paths": ["swarm.html", "swarm.js"],
                "receipt_present": True,
            }
        )
        self.assertEqual(verdict["state"], "CANDIDATE")
        self.assertIn("swarm.css", verdict["note"])

    def test_receipt_and_sources_are_integrated(self):
        verdict = classify(
            {
                "measured": True,
                "source_id": DEFAULT_ID,
                "source_paths": list(DEFAULT_PATHS),
                "present_paths": list(DEFAULT_PATHS),
                "receipt_present": True,
            }
        )
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_live_tree_is_carrier_only_for_the_demon_id(self):
        row = measure_root(ROOT)
        self.assertTrue(row["measured"])
        self.assertTrue(row["catalog_present"])
        self.assertEqual(row["source_id"], DEFAULT_ID)
        self.assertEqual(row["source_paths"], list(DEFAULT_PATHS))
        self.assertEqual(row["present_paths"], list(DEFAULT_PATHS))
        self.assertFalse(row["receipt_present"])
        self.assertEqual(row["receipt_path"], "p/%s.md" % DEFAULT_ID)
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertIn("demon-pixel-swarm-flight-recorder-landed-20260825-01", row["hands_off"])
        verdict = classify(row)
        self.assertEqual(verdict["state"], "CARRIER_ONLY")

    def test_catalog_names_the_slack_claim(self):
        catalog_path = os.path.join(ROOT, "ground", "SLACK_RECEIPT.json")
        with open(catalog_path, "r", encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["source_id"], DEFAULT_ID)
        self.assertEqual(catalog["source_paths"], list(DEFAULT_PATHS))
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(
            catalog["claimed_sha"],
            "f84b46b5c2467405e62663cfa589eadd57369cfe",
        )
        self.assertEqual(present_paths(["swarm.html"], ["swarm.html"]), ["swarm.html"])
        self.assertEqual(receipt_path(DEFAULT_ID), "p/%s.md" % DEFAULT_ID)

    def test_empty_catalog_tree_is_not_landed(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = measure_root(tmp)
            self.assertTrue(row["measured"])
            self.assertFalse(row["catalog_present"])
            self.assertFalse(row["receipt_present"])
            self.assertEqual(row["present_paths"], [])
            self.assertEqual(classify(row)["state"], "NOT_LANDED")


if __name__ == "__main__":
    unittest.main()
