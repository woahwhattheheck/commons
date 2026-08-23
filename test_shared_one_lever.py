#!/usr/bin/env python3
"""The shared-one lever is a measurement, not a Slack essay."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))
from shared_one_lever import EXCERPT_DIR, census, list_excerpts, measure_path

LVIN = os.path.join(EXCERPT_DIR, "muhl_lvin.mno")
ESNR = os.path.join(EXCERPT_DIR, "muhl_esnr.mno")
IMMN = os.path.join(EXCERPT_DIR, "muhl_immn.mno")


class TestSharedOneLever(unittest.TestCase):
    def test_const1_is_a_written_one_on_every_excerpt(self):
        paths = list_excerpts(EXCERPT_DIR)
        self.assertGreaterEqual(len(paths), 19, "PLUMB 1-19 excerpts missing")
        data = census(paths)
        self.assertEqual(data["titan"], "NOT_WRITTEN")
        self.assertEqual(data["const1_written"], data["excerpts"])
        self.assertGreaterEqual(data["const1_shared"], 16)
        for row in data["rows"]:
            self.assertEqual(row["const0_written"], 0, row["path"])
            self.assertEqual(row["const1_written"], 1, row["path"])
            self.assertTrue(row["unique_out_eq_gates"], row["path"])
            self.assertEqual(row["file_levels"], 256, row["path"])
            self.assertEqual(row["plane_levels"], 2, row["path"])
            self.assertGreater(row["share_factor"], 1.0, row["path"])

    def test_lvin_one_written_one_feeds_1901_gates(self):
        self.assertTrue(os.path.isfile(LVIN), "muhl_lvin.mno is the densest shared-one excerpt")
        row = measure_path(LVIN)
        self.assertEqual(row["magic"], "MUHLLVIN")
        self.assertEqual(row["n_gate"], 2368)
        self.assertEqual(row["const1_addr"], 541)
        self.assertEqual(row["const1_written"], 1)
        self.assertEqual(row["share1"], 1901)
        self.assertGreater(row["share_factor"], 8.0)
        self.assertEqual(row["hottest_addr"], 541)
        self.assertEqual(row["hottest_fan"], 1901)

    def test_esnr_and_immn_overlap_stay_on_the_written_charge(self):
        esnr = measure_path(ESNR)
        immn = measure_path(IMMN)
        self.assertEqual(esnr["share1"], 4132)
        self.assertEqual(esnr["share0"], 12288)
        self.assertEqual(immn["hottest_addr"], 36)
        self.assertEqual(immn["hottest_fan"], 14391)
        self.assertEqual(immn["share1"], 2249)


if __name__ == "__main__":
    unittest.main()
