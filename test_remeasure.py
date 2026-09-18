#!/usr/bin/env python3
"""Remeasure leftover runs Claude's X as a non-Claude seat; it is never 0."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from remeasure import (
    BAKE_SCAN,
    CALIBRATION,
    PACKET,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    SOURCE_ID,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
    phrase_hits,
    planted_deletion_canary,
)


class TestRemeasure(unittest.TestCase):
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
                "canary_ok": True,
            }
        )
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("instrument failure", verdict["note"])
        self.assertIn("Never 0", verdict["note"])
        self.assertEqual(verdict["z"], "FINDER-FAILED")

    def test_failed_canary_voids_empty_deletions(self):
        verdict = classify(
            {
                "measured": True,
                "calibration_ok": True,
                "canary_ok": False,
                "card_present": True,
                "catalog_present": True,
            }
        )
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("planted-deletion canary", verdict["note"])
        self.assertEqual(verdict["z"], "FINDER-FAILED")

    def test_missing_paths_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "misses": ["ground/REMEASURE.md"],
                "calibration_ok": True,
                "canary_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertEqual(verdict["z"], "FINDER-FAILED")

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "found_phrases": list(REQUIRED_PHRASES),
                "artifacts": [
                    {"artifact": "a", "status": "RETRACTED"},
                    {"artifact": "b", "status": "RETRACTED"},
                    {"artifact": "c", "status": "EVIDENCE-PENDING"},
                    {"artifact": "d", "status": "UNSCANNED"},
                    {"artifact": "e", "status": "CORRECTED"},
                ],
                "packet_present": True,
                "canary_ok": True,
                "remeasurement_owner": "Codex / Grok Build",
                "allowed_remeasurers": [
                    "deterministic local checks",
                    "GitHub Actions",
                    "Codex",
                    "Codex / Grok Build",
                ],
                "xyz_required": True,
                "label": "EVIDENCE-PENDING-NON-CLAUDE-REMEASURE",
                "calibration_ok": True,
                "calibration_hits": list(CALIBRATION),
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_planted_deletion_canary_sees_the_delete(self):
        canary = planted_deletion_canary()
        self.assertTrue(canary["ok"], canary)
        self.assertIn("planted-deletion-canary.txt", canary["names"])

    def test_head_phrase_miss_is_unverified_never_zero(self):
        missing = phrase_hits(ROOT, "this-phrase-is-not-on-any-post-remeasure-20260825")
        self.assertEqual(missing["z"], "FINDER-UNVERIFIED")
        self.assertEqual(missing["hits"], [])
        self.assertIn("Never 0", missing["note"])
        self.assertNotEqual(missing["note"], "0")

    def test_live_tree_matches_the_report(self):
        catalog_path = os.path.join(ROOT, "ground", "REMEASURE.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["source_id"], SOURCE_ID)
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertEqual(catalog["label"], "EVIDENCE-PENDING-NON-CLAUDE-REMEASURE")
        self.assertTrue(catalog["xyz_required"])
        self.assertEqual(catalog["remeasurement_owner"], "Codex / Grok Build")
        self.assertGreaterEqual(len(catalog["allowed_remeasurers"]), 4)
        self.assertGreaterEqual(len(catalog["artifacts"]), 5)
        row = measure_root(ROOT)
        self.assertTrue(row["calibration_ok"], "known-present calibration must hit HEAD + Action Pad")
        self.assertEqual(sorted(row["calibration_hits"]), sorted(CALIBRATION))
        self.assertEqual(row["search_space"], list(SEARCH_SPACE))
        self.assertTrue(row["packet_present"], "packet must exist at excerpts/20260823/")
        self.assertTrue(row["canary_ok"], "planted-deletion canary must PASS")
        self.assertFalse(row["bake_scan_present"], "pfc_bake_scan.py stays off current main")
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        self.assertIn("containment_compliance", row["found_phrases"])
        self.assertIn("7-term space-separated", row["found_phrases"])
        kite = [item for item in row["head_phrases"] if item["phrase"] == "kite-help"]
        self.assertTrue(kite and kite[0]["hits"], "kite-help claims are files on current main")
        stranded = [
            item
            for item in row["head_phrases"]
            if item["phrase"] == "stranded-LocalDeviceAgent"
        ]
        self.assertTrue(stranded and stranded[0]["hits"], "stranded-LocalDeviceAgent claims are files on current main")
        self.assertEqual(stranded[0]["z"], "")
        self.assertIn("Y from found bytes", stranded[0]["note"])
        self.assertFalse(os.path.isfile(os.path.join(ROOT, BAKE_SCAN)))
        self.assertTrue(os.path.isfile(os.path.join(ROOT, PACKET)))


if __name__ == "__main__":
    unittest.main()
