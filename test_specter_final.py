#!/usr/bin/env python3
"""SPECTER FINAL leftover classifies a Slack current-main SHA."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from specter_final import (
    ALREADY_LANDED,
    CALIBRATION,
    CITED_SHA,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    classify,
    classify_sha,
    load_catalog,
    measure_from_rows,
    measure_root,
)


class TestSpecterFinal(unittest.TestCase):
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

    def test_missing_card_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "misses": ["ground/SPECTER_FINAL.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_unmeasured_sha_is_not_stillness(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "sha_relation": "UNMEASURED",
                "search_space": list(SEARCH_SPACE),
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("never 0", verdict["note"].lower())

    def test_foreign_sha_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "sha_relation": "FOREIGN",
                "cited_sha": CITED_SHA,
                "official_head": "deadbeef",
                "specter_bytes_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("not an ancestor", verdict["note"])

    def test_ancestor_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "sha_relation": "ANCESTOR",
                "cited_sha": CITED_SHA,
                "official_head": "6aa069e7a92c63f862d7d009de3c721482e51832",
                "specter_bytes_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])
        self.assertIn("ANCESTOR", verdict["note"])

    def test_classify_sha_relations(self):
        self.assertEqual(classify_sha(CITED_SHA, CITED_SHA, False), "HEAD")
        self.assertEqual(classify_sha(CITED_SHA, "abc" * 14, True), "ANCESTOR")
        self.assertEqual(classify_sha(CITED_SHA, "abc" * 14, False), "FOREIGN")
        self.assertEqual(classify_sha("", "", False), "UNMEASURED")

    def test_live_tree_measures_integrated(self):
        row = measure_root(ROOT)
        verdict = classify(row)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertTrue(row["specter_bytes_present"])
        self.assertIn(row["sha_relation"], ("HEAD", "ANCESTOR"))
        self.assertEqual(verdict["state"], "INTEGRATED", verdict)
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertEqual(row.get("idle_resume"), "UNMEASURED")
        self.assertFalse(row["landed_missing"])
        self.assertEqual(row.get("slack_ts") or SLACK_TS, SLACK_TS)
        self.assertEqual(row.get("cited_sha"), CITED_SHA)

    def test_catalog_names_cited_sha(self):
        catalog_path = os.path.join(ROOT, "ground", "SPECTER_FINAL.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["cited_sha"], CITED_SHA)
        self.assertEqual(catalog["cited_sha_role"], "ancestor_not_current_head")
        self.assertEqual(catalog["posting"], "OPEN")
        self.assertTrue(catalog["no_auth"])
        self.assertTrue(catalog["no_gate"])
        self.assertEqual(catalog["idle_resume"], "UNMEASURED")
        self.assertIn("ground/TERMINAL_CATALOG.md", catalog["already_landed"])

    def test_search_space_and_calibration_named(self):
        self.assertIn("ground/SPECTER_FINAL.md", SEARCH_SPACE)
        self.assertIn("host/specter_final.py", SEARCH_SPACE)
        self.assertIn("ground/EXECUTE.md", CALIBRATION)
        self.assertIn("ground/TERMINAL_CATALOG.md", ALREADY_LANDED)
        self.assertIn("wake_jobs/specter-watchdog-head-proof-20260825-01.json", ALREADY_LANDED)


if __name__ == "__main__":
    unittest.main()
