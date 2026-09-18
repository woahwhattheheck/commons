#!/usr/bin/env python3
"""Working-builds leftover measures; it does not upload Desktop bytes."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from working_builds import (
    KEYB_CONTAINER_SHA,
    SLACK_TS,
    classify,
    load_catalog,
    measure_from_rows,
    measure_tree,
)


class TestWorkingBuilds(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_current_main_facts_are_quarantined(self):
        measured = measure_from_rows(
            {
                "rook_package": False,
                "rook_resume": True,
                "keyb_manifest": True,
                "keyb_container": False,
                "keyb_fab": True,
                "keyb_check": "refuse_forbidden_dest",
                "train_json": False,
                "train_post": True,
                "refuse_upload": True,
            }
        )
        self.assertEqual(measured["rook"], "STRANDED")
        self.assertEqual(measured["rook_disposition"], "QUARANTINE")
        self.assertEqual(measured["keyb"], "STRANDED")
        self.assertEqual(measured["keyb_disposition"], "QUARANTINE")
        self.assertEqual(measured["titan_census"], "STRANDED")
        self.assertEqual(measured["titan_disposition"], "UNRECONCILED")
        self.assertEqual(measured["titan_original_disposition"], "SUPERSEDED")
        self.assertEqual(measured["keyb_hash_state"], "STALE")
        self.assertFalse(measured["keyb_verified"])
        self.assertEqual(classify(measured)["state"], "INTEGRATED")
        self.assertIn("Slack list is still not the file", classify(measured)["note"])

    def test_upload_flag_blocks_land(self):
        measured = measure_from_rows(
            {
                "rook_package": False,
                "rook_resume": True,
                "keyb_manifest": True,
                "keyb_container": False,
                "keyb_fab": True,
                "train_json": False,
                "train_post": True,
                "refuse_upload": False,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")
        self.assertIn("Do not upload", classify(measured)["note"])

    def test_missing_train_post_is_not_landed(self):
        measured = measure_from_rows({"rook_package": False, "rook_resume": True})
        self.assertEqual(measured["titan_census"], "NOT_LANDED")
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_live_tree_matches_the_report(self):
        catalog_path = os.path.join(ROOT, "ground", "WORKING_BUILDS.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog_text = handle.read()
        catalog = load_catalog(catalog_text)
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertTrue(catalog["refuse_upload"])
        self.assertEqual(len(catalog["artifacts"]), 3)
        row = measure_tree(ROOT, catalog_text)
        self.assertTrue(row["measured"])
        self.assertFalse(row["rook_package"])
        self.assertTrue(row["rook_resume"])
        self.assertEqual(row["rook"], "STRANDED")
        self.assertEqual(row["rook_disposition"], "QUARANTINE")
        self.assertTrue(row["keyb_manifest"])
        self.assertFalse(row["keyb_container"])
        self.assertTrue(row["keyb_fab"])
        self.assertEqual(row["keyb_check"], "refuse_forbidden_dest")
        self.assertEqual(row["keyb"], "STRANDED")
        self.assertEqual(row["keyb_disposition"], "QUARANTINE")
        self.assertEqual(row["keyb_sha256"], KEYB_CONTAINER_SHA)
        self.assertEqual(row["keyb_hash_state"], "STALE")
        self.assertFalse(row["keyb_verified"])
        self.assertFalse(row["train_json"])
        self.assertTrue(row["train_post"])
        self.assertEqual(row["titan_census"], "STRANDED")
        self.assertEqual(row["titan_disposition"], "UNRECONCILED")
        self.assertEqual(row["titan_original_disposition"], "SUPERSEDED")
        self.assertEqual(row["titan_write"], "NOT_WRITTEN")
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        self.assertIn("rook-resident-native", " ".join(row["absent_paths"]))
        self.assertIn("keyb01.mno", " ".join(row["absent_paths"]))
        self.assertIn("TRAIN_CIRCUITS_FROM_FILE.json", " ".join(row["absent_paths"]))


if __name__ == "__main__":
    unittest.main()
