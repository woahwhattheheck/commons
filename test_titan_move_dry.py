#!/usr/bin/env python3
"""Titan MOVE dry measure is a measurement, not a titan write."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from titan_move_dry import classify, measure_from_packet, measure_tree, owner_blocker


class TestTitanMoveDry(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_missing_excerpts_are_not_landed(self):
        measured = {
            "measured": True,
            "count": 12,
            "excerpt_count": 12,
            "titan": "NOT_WRITTEN",
            "nonzero_offsets": 0,
            "reread": False,
        }
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("12/31", verdict["note"])

    def test_thirty_one_excerpts_without_write_are_not_landed(self):
        measured = {
            "measured": True,
            "count": 31,
            "excerpt_count": 31,
            "titan": "NOT_WRITTEN",
            "nonzero_offsets": 0,
            "reread": False,
        }
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("OWNER_LOCAL_ALLOCATOR", verdict["note"])
        self.assertIn("31/31", verdict["note"])

    def test_written_and_reread_is_integrated(self):
        measured = {
            "measured": True,
            "count": 31,
            "excerpt_count": 31,
            "titan": "WRITTEN",
            "nonzero_offsets": 31,
            "reread": True,
        }
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("31", verdict["note"])

    def test_packet_parser_counts_zero_offsets(self):
        packet = {
            "kind": "TITAN_MOVE_PACKET",
            "titan": "NOT_WRITTEN",
            "count": 1,
            "organs": [
                {
                    "container": "muhl_hdvs.mno",
                    "offset": 0,
                    "sha256": "x",
                }
            ],
        }
        excerpt_dir = os.path.join(ROOT, "excerpts", "20260823")
        row = measure_from_packet(packet, excerpt_dir)
        self.assertTrue(row["measured"])
        self.assertEqual(row["excerpt_count"], 1)
        self.assertEqual(row["nonzero_offsets"], 0)
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertFalse(row["reread"])

    def test_live_tree_is_thirty_one_and_not_written(self):
        row = measure_tree(ROOT)
        self.assertTrue(row["measured"], row)
        self.assertGreaterEqual(row["excerpt_count"], 31)
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertEqual(row["nonzero_offsets"], 0)
        self.assertFalse(row["reread"])
        verdict = classify(row)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        blocker = owner_blocker(row, verdict)
        self.assertIn("OWNER_LOCAL_ALLOCATOR", blocker["WHY_ONLY_BRYCE"])
        self.assertIn("titan.gguf", blocker["NEED"])


if __name__ == "__main__":
    unittest.main()
