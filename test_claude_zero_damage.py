#!/usr/bin/env python3
"""Claude-zero-damage leftover measures; it does not overwrite history."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from claude_zero_damage import (
    FINDER_FAILED,
    REQUIRED_INCIDENT_IDS,
    SLACK_TS,
    STALE_SHA,
    calibrate,
    classify,
    claude_tester_authority,
    load_catalog,
    measure_from_rows,
    measure_tree,
    search_space,
)


class TestClaudeZeroDamage(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])
        self.assertEqual(row["z"], FINDER_FAILED)
        self.assertNotEqual(row["z"], "0")
        self.assertNotEqual(row["z"], 0)

    def test_miss_never_prints_zero(self):
        space = search_space()
        self.assertEqual(space["z"], FINDER_FAILED)
        self.assertIn("WORKING_BUILDS.json", space["working"])
        miss = classify({"measured": False})
        self.assertEqual(miss["z"], FINDER_FAILED)
        self.assertNotIn(" 0", " %s " % miss["z"])

    def test_calibration_hits_head(self):
        hit = calibrate(ROOT)
        self.assertTrue(hit["ok"])
        self.assertIn("bake is not the board", hit["y"].lower())
        self.assertGreater(hit["bytes"], 0)

    def test_tester_authority_needles(self):
        self.assertTrue(claude_tester_authority("assigned review authority"))
        self.assertTrue(claude_tester_authority("Claude is the tester"))
        self.assertFalse(
            claude_tester_authority(
                "informational evidence only; not tester/verifier/QA"
            )
        )

    def test_frozen_titan_is_not_landed(self):
        measured = measure_from_rows(
            {
                "calibration": {"ok": True, "y": "present"},
                "never_print_zero": True,
                "preserve_originals": True,
                "incidents": [
                    {
                        "id": name,
                        "x": "x",
                        "y": "y",
                        "z": FINDER_FAILED,
                        "consumer": "c",
                        "repair": "r",
                    }
                    for name in REQUIRED_INCIDENT_IDS
                ],
                "retracted": [
                    {"id": "keyb-verified-sha-a63396"},
                    {"id": "titan-superseded-from-absence"},
                ],
                "keyb": {"hash_state": "STALE", "verified": False},
                "titan": {"disposition": "SUPERSEDED"},
                "claude": {"assigned_backlog": "informational only"},
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")
        self.assertIn("SUPERSEDED-from-absence", classify(measured)["note"])

    def test_live_tree_retracts_frozen_numbers(self):
        catalog_path = os.path.join(ROOT, "ground", "CLAUDE_ZERO_DAMAGE.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog_text = handle.read()
        catalog = load_catalog(catalog_text)
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertTrue(catalog["never_print_zero"])
        self.assertTrue(catalog["preserve_originals"])
        ids = [row["id"] for row in catalog["incidents"]]
        for name in REQUIRED_INCIDENT_IDS:
            self.assertIn(name, ids)
        row = measure_tree(ROOT, catalog_text)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertTrue(row["keyb_stale"])
        self.assertFalse(row["keyb_verified"])
        self.assertEqual(row["keyb_sha256"], STALE_SHA)
        self.assertEqual(row["titan_disposition"], "UNRECONCILED")
        self.assertEqual(row["titan_original_disposition"], "SUPERSEDED")
        self.assertTrue(row["titan_unreconciled"])
        self.assertFalse(row["claude_tester_authority"])
        self.assertEqual(row["z"], FINDER_FAILED)
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        self.assertIn("still not the file", classify(row)["note"])


if __name__ == "__main__":
    unittest.main()
