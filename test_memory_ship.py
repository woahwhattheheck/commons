#!/usr/bin/env python3
"""Memory-ship leftover names unused ROLE-only boards and requires a main SHA."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "host"))

import memory_board
from memory_ship import (
    ALREADY_LANDED,
    CALIBRATION,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
)


class TestMemoryShip(unittest.TestCase):
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
                "misses": ["ground/MEMORY_SHIP.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_gate_flag_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "closes_door": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("close the door", verdict["note"].lower())

    def test_missing_ship_column_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "has_ship_state": True,
                "has_ship_column": False,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "closes_door": False,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("ship", verdict["note"].lower())

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "has_ship_state": True,
                "has_ship_column": True,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "closes_door": False,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_role_only_is_unused_even_with_sha(self):
        board = {
            "entries": [
                {
                    "kind": "ROLE",
                    "body": "integrated at merge 15ed04d0c2061674c15e9d5b7ccc00a9f3ab43ec",
                    "entry_id": "kite-memory-create-01",
                    "ts": "2026-08-21T17:14:48Z",
                }
            ]
        }
        self.assertEqual(memory_board.ship_state_for_board(board), "UNUSED")

    def test_work_state_without_sha_is_talk(self):
        board = {
            "entries": [
                {"kind": "ROLE", "body": "role", "entry_id": "a", "ts": "2026-08-25T07:00:00Z"},
                {"kind": "WORK_STATE", "body": "working on it", "entry_id": "b", "ts": "2026-08-25T07:01:00Z"},
            ]
        }
        self.assertEqual(memory_board.ship_state_for_board(board), "TALK")

    def test_work_state_with_sha_is_shipped(self):
        board = {
            "entries": [
                {"kind": "ROLE", "body": "role", "entry_id": "a", "ts": "2026-08-25T07:00:00Z"},
                {
                    "kind": "WORK_STATE",
                    "body": "INTEGRATED — VERIFIED ON CURRENT MAIN f16da14f264eddd3c0b67bdc924b9ecb543ee689",
                    "entry_id": "b",
                    "ts": "2026-08-25T07:01:00Z",
                },
            ]
        }
        self.assertEqual(memory_board.ship_state_for_board(board), "SHIPPED")

    def test_live_tree_measures_integrated(self):
        row = measure_root(ROOT)
        verdict = classify(row)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertFalse(row["landed_missing"])
        self.assertEqual(row.get("slack_ts") or SLACK_TS, SLACK_TS)

    def test_catalog_parses(self):
        catalog_path = os.path.join(ROOT, "ground", "MEMORY_SHIP.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["posting"], "OPEN")
        self.assertTrue(catalog["no_auth"])
        self.assertTrue(catalog["no_gate"])
        self.assertNotIn("memory_is_gate", catalog)
        self.assertIn("memory_board.py", catalog["already_landed"])

    def test_search_space_and_calibration_named(self):
        self.assertIn("ground/MEMORY_SHIP.md", SEARCH_SPACE)
        self.assertIn("memory_board.py", SEARCH_SPACE)
        self.assertIn("memory_board.py", CALIBRATION)
        self.assertIn("ground/EXECUTE.md", CALIBRATION)
        self.assertIn("ground/SITTING_REMINT.md", ALREADY_LANDED)


if __name__ == "__main__":
    unittest.main()
