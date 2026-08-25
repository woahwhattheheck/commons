#!/usr/bin/env python3
"""Recovered PFC bake census is a catalog, not Slack talk."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from pfc_bake_census import classify, measure_path, parse_catalog


class TestPfcBakeCensus(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_partial_map_is_not_landed(self):
        measured = parse_catalog(
            "| Llama-3.3-70B | `token_embd` 130 (4369–5966) |\n"
            "Heuristic detector. LOWER BOUNDS. READ-ONLY.\n"
        )
        self.assertEqual(measured["models"], 1)
        self.assertEqual(measured["regions"], 1)
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("want 17/7", verdict["note"])

    def test_live_catalog_is_integrated(self):
        path = os.path.join(ROOT, "docs", "PFC_BAKE_CENSUS.md")
        measured = measure_path(path)
        self.assertTrue(measured["measured"])
        self.assertEqual(measured["models"], 7)
        self.assertEqual(measured["regions"], 17)
        self.assertTrue(measured["has_caveats"])
        self.assertEqual(measured["titan"], "NOT_WRITTEN")
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("17 regions", verdict["note"])

    def test_missing_file_is_unmeasured(self):
        measured = measure_path(os.path.join(ROOT, "docs", "NO_SUCH_CENSUS.md"))
        self.assertFalse(measured["measured"])
        self.assertEqual(classify(measured)["state"], "UNMEASURED")


if __name__ == "__main__":
    unittest.main()
