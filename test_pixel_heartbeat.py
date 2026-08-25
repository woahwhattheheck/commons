#!/usr/bin/env python3
"""Pixel-heartbeat leftover measures; it does not invent presence."""

from __future__ import annotations

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from pixel_heartbeat import (
    catalog_from_row,
    classify,
    load_index,
    measure_from_rows,
    measure_root,
    parse_heartbeat,
    reconcile_index,
)


class TestPixelHeartbeat(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_missing_index_is_not_landed(self):
        measured = measure_from_rows(None, [])
        self.assertFalse(measured["index_present"])
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_empty_pixels_is_not_landed(self):
        measured = measure_from_rows("[]", [])
        self.assertTrue(measured["index_present"])
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")
        self.assertIn("Do not invent", classify(measured)["note"])

    def test_stale_player2_is_candidate(self):
        now = "2026-08-25T05:18:00Z"
        measured = measure_from_rows(
            '["PLAYER2.json"]',
            [
                {
                    "name": "PLAYER2.json",
                    "text": json.dumps(
                        {
                            "from": "PLAYER2",
                            "path": "COMMONS_PUT/pixel.html",
                            "verb": "building pixel floor",
                            "on": "pc",
                            "ts": "2026-08-20T11:05:00Z",
                            "src": "Cursor side chat — PLAYER2.",
                        }
                    ),
                }
            ],
            now,
        )
        self.assertEqual(measured["stale"], ["PLAYER2.json"])
        self.assertFalse(measured["fabricate"])
        self.assertEqual(measured["titan"], "NOT_WRITTEN")
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "CANDIDATE")
        self.assertIn("stale: PLAYER2.json", verdict["note"])

    def test_fresh_valid_heartbeat_is_integrated(self):
        now = "2026-08-25T05:18:00Z"
        measured = measure_from_rows(
            '["PLAYER2.json"]',
            [
                {
                    "name": "PLAYER2.json",
                    "text": json.dumps(
                        {
                            "from": "PLAYER2",
                            "path": "pixel.html",
                            "verb": "building",
                            "on": "pc",
                            "ts": "2026-08-25T04:30:00Z",
                            "src": "session wrote pixel.html",
                            "sha": "da27d5b21",
                        }
                    ),
                }
            ],
            now,
        )
        self.assertEqual(measured["hot"], ["PLAYER2.json"])
        self.assertEqual(classify(measured)["state"], "INTEGRATED")

    def test_guessed_src_is_fabricated(self):
        measured = measure_from_rows(
            '["DEMON.json"]',
            [
                {
                    "name": "DEMON.json",
                    "text": json.dumps(
                        {
                            "from": "DEMON",
                            "ts": "2026-08-25T04:00:00Z",
                            "src": "guessed search",
                        }
                    ),
                }
            ],
            "2026-08-25T05:00:00Z",
        )
        self.assertEqual(measured["fabricated"], ["DEMON.json"])
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "CANDIDATE")
        self.assertIn("invent presence", verdict["note"])

    def test_claim_mismatch_is_fabricated(self):
        row = parse_heartbeat(
            "PLAYER2.json",
            json.dumps(
                {
                    "from": "DEMON",
                    "ts": "2026-08-25T04:00:00Z",
                    "src": "local session",
                }
            ),
        )
        self.assertTrue(row["fabricated"])
        self.assertEqual(row["from"], "DEMON")
        self.assertEqual(row["claim"], "PLAYER2")

    def test_index_reconciliation(self):
        recon = reconcile_index(["PLAYER2.json", "MISSING.json"], ["PLAYER2.json", "EXTRA.json"])
        self.assertEqual(recon["listed_missing"], ["MISSING.json"])
        self.assertEqual(recon["unlisted"], ["EXTRA.json"])
        self.assertEqual(load_index('["PLAYER2"]'), ["PLAYER2.json"])
        self.assertEqual(load_index("{"), [])

    def test_catalog_names_hands_off(self):
        catalog = catalog_from_row(
            {
                "listed": ["PLAYER2.json"],
                "files": ["PLAYER2.json"],
                "stale": ["PLAYER2.json"],
                "heartbeats": [
                    {
                        "name": "PLAYER2.json",
                        "from": "PLAYER2",
                        "freshness": "STALE",
                        "fabricated": False,
                        "valid": True,
                    }
                ],
            }
        )
        self.assertEqual(catalog["source_id"], "demon-side-harness-offer-20260825-01")
        self.assertFalse(catalog["fabricate"])
        self.assertIn("rivet-render-check-ci", catalog["hands_off"])
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")

    def test_live_tree_measures_stale_player2(self):
        measured = measure_root(ROOT, "2026-08-25T05:18:00Z")
        self.assertTrue(measured["measured"])
        self.assertTrue(measured["index_present"])
        self.assertIn("PLAYER2.json", measured["files"])
        self.assertEqual(measured["listed_missing"], [])
        self.assertEqual(measured["unlisted"], [])
        self.assertFalse(measured["fabricate"])
        self.assertEqual(measured["titan"], "NOT_WRITTEN")
        self.assertEqual(measured["stale"], ["PLAYER2.json"])
        self.assertEqual(classify(measured)["state"], "CANDIDATE")


if __name__ == "__main__":
    unittest.main()
