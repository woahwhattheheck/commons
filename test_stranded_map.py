#!/usr/bin/env python3
"""Stranded-map leftover measures; it does not take assigned lanes."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from stranded_map import (
    LATER_SIZE,
    PACKET_SIZE,
    classify,
    load_catalog,
    measure_from_rows,
    measure_tree,
)


class TestStrandedMap(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_current_main_facts_are_stranded(self):
        measured = measure_from_rows(
            {
                "lda_android": True,
                "gh_android": False,
                "wake_job_json": 0,
                "mcp_surfaces": [
                    "commons_mcp.py",
                    "independent_commons_mcp",
                    "door/src/mcp.server.ts",
                    "mcp_server",
                ],
                "mcp_inventory": False,
                "whitebox_source": True,
                "whitebox_customer_receipt": False,
                "bazaar_offers": 7,
                "bazaar_copy_node": False,
                "titan_packet_size": PACKET_SIZE,
                "titan_later_size": LATER_SIZE,
            }
        )
        self.assertEqual(measured["android"], "STRANDED")
        self.assertEqual(measured["wake"], "EMPTY")
        self.assertEqual(measured["mcp"], "FRAGMENTED")
        self.assertEqual(measured["whitebox"], "PROPOSED")
        self.assertEqual(measured["bazaar"], "UNFULFILLED")
        self.assertEqual(measured["titan"], "STALE")
        self.assertEqual(classify(measured)["state"], "INTEGRATED")
        self.assertIn("Slack map is still not the file", classify(measured)["note"])

    def test_done_canary_is_verified(self):
        measured = measure_from_rows(
            {
                "lda_android": True,
                "gh_android": False,
                "wake_job_json": 2,
                "wake_jobs": [
                    {
                        "job_id": "rivet-watchdog-canary-20260825-01",
                        "status": "DONE",
                    },
                    {
                        "job_id": "specter-watchdog-head-proof-20260825-01",
                        "status": "DONE",
                    }
                ],
                "mcp_surfaces": [
                    "commons_mcp.py",
                    "independent_commons_mcp",
                    "door/src/mcp.server.ts",
                    "mcp_server",
                ],
                "mcp_inventory": True,
                "whitebox_source": True,
                "whitebox_customer_receipt": False,
                "bazaar_offers": 7,
                "bazaar_copy_node": False,
                "titan_packet_size": PACKET_SIZE,
                "titan_later_size": LATER_SIZE,
            }
        )
        self.assertEqual(measured["wake"], "VERIFIED")
        self.assertEqual(classify(measured)["state"], "INTEGRATED")

    def test_open_canary_is_candidate(self):
        measured = measure_from_rows(
            {
                "lda_android": True,
                "gh_android": False,
                "wake_job_json": 2,
                "wake_jobs": [
                    {
                        "job_id": "rivet-watchdog-canary-20260825-01",
                        "status": "DONE",
                    },
                    {
                        "job_id": "specter-watchdog-head-proof-20260825-01",
                        "status": "OPEN",
                    }
                ],
                "titan_packet_size": PACKET_SIZE,
                "titan_later_size": LATER_SIZE,
            }
        )
        self.assertEqual(measured["wake"], "CANDIDATE")

    def test_missing_titan_size_is_not_landed(self):
        measured = measure_from_rows({"lda_android": True, "gh_android": False})
        self.assertEqual(measured["titan"], "UNMEASURED")
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_live_tree_matches_the_map(self):
        catalog_path = os.path.join(ROOT, "ground", "STRANDED_MAP.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog_text = handle.read()
        catalog = load_catalog(catalog_text)
        self.assertEqual(catalog["slack_ts"], "1787635487.642039")
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        row = measure_tree(ROOT, catalog_text)
        self.assertTrue(row["measured"])
        self.assertTrue(row["lda_android"])
        self.assertFalse(row["gh_android"])
        self.assertEqual(row["android"], "STRANDED")
        self.assertGreaterEqual(row["wake_job_json"], 1)
        self.assertEqual(row["wake"], "VERIFIED")
        self.assertGreaterEqual(len(row["wake_jobs"]), 2)
        self.assertTrue(
            all(item["status"] == "DONE" for item in row["wake_jobs"])
        )
        self.assertGreaterEqual(len(row["mcp_surfaces"]), 4)
        self.assertTrue(row["mcp_inventory"])
        self.assertEqual(row["mcp"], "INTEGRATED")
        self.assertEqual(row["whitebox"], "PROPOSED")
        self.assertEqual(row["bazaar_offers"], 7)
        self.assertFalse(row["bazaar_copy_node"])
        self.assertEqual(row["bazaar"], "UNFULFILLED")
        self.assertEqual(row["titan"], "STALE")
        self.assertEqual(row["titan_write"], "NOT_WRITTEN")
        self.assertEqual(classify(row)["state"], "INTEGRATED")


if __name__ == "__main__":
    unittest.main()
