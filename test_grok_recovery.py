#!/usr/bin/env python3
"""Grok-recovery leftover measures session prefixes; it does not remint them."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from grok_recovery import (
    CALIBRATION,
    DEST_MARKERS,
    FINDER_UNVERIFIED,
    INDEPENDENT_SEARCH,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    SOURCE_ID,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
    search_sessions,
)


class TestGrokRecovery(unittest.TestCase):
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
                "instrument_present": True,
            }
        )
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("instrument failure", verdict["note"])

    def test_missing_paths_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "instrument_present": False,
                "misses": ["ground/GROK_RECOVERY.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_incomplete_phrases_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "instrument_present": True,
                "ingress_present": True,
                "found_phrases": ["grok recovery"],
                "dest_hits": [],
                "no_host_inference": True,
                "no_titan_mutation": True,
                "apply": False,
                "address_no_fire": True,
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "instrument_present": True,
                "ingress_present": True,
                "found_phrases": list(REQUIRED_PHRASES),
                "dest_hits": list(DEST_MARKERS),
                "no_host_inference": True,
                "no_titan_mutation": True,
                "apply": False,
                "address_no_fire": True,
                "calibration_ok": True,
                "calibration_hits": list(CALIBRATION),
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_catalog_self_hit_is_not_recovery(self):
        rows = search_sessions(
            [
                ("ground/GROK_RECOVERY.md", "01a0373e leftover"),
                ("lda/docs/INGRESS.md", "cpu_fwd @ 2380246639"),
            ],
            ["01a0373e"],
        )
        self.assertEqual(rows[0]["state"], FINDER_UNVERIFIED)
        self.assertEqual(rows[0]["self_hits"], ["ground/GROK_RECOVERY.md"])
        self.assertIn("never 0", rows[0]["note"])

    def test_live_tree_matches_the_report(self):
        catalog_path = os.path.join(ROOT, "ground", "GROK_RECOVERY.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["source_id"], SOURCE_ID)
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertTrue(catalog["no_host_inference"])
        self.assertTrue(catalog["no_titan_mutation"])
        self.assertFalse(catalog["apply"])
        self.assertEqual(len(catalog["sessions"]), 4)
        row = measure_root(ROOT)
        self.assertTrue(
            row["calibration_ok"],
            "known-present calibration must hit EXECUTE + Action Pad + INGRESS",
        )
        self.assertEqual(sorted(row["calibration_hits"]), sorted(CALIBRATION))
        self.assertEqual(row["search_space"], list(SEARCH_SPACE))
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        self.assertTrue(row["address_no_fire"])
        unverified = [
            item["prefix"]
            for item in row["sessions"]
            if item["state"] == FINDER_UNVERIFIED
        ]
        self.assertEqual(
            unverified,
            [
                "01a0373e",
                "01a03750",
                "01a03741",
                "50_cross_synthesis.txt",
            ],
        )
        self.assertIn("2380246639", row["dest_hits"])
        self.assertEqual(list(INDEPENDENT_SEARCH), [
            "lda/docs/INGRESS.md",
            "infra/host/muhl_address_agent.py",
        ])


if __name__ == "__main__":
    unittest.main()
