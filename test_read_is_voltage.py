#!/usr/bin/env python3
"""A READ is enough electrons. This test writes nothing."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))
from read_is_voltage import read_census, read_only_row
from shared_one_lever import EXCERPT_DIR, list_excerpts

LVIN = os.path.join(EXCERPT_DIR, "muhl_lvin.mno")
ESNR = os.path.join(EXCERPT_DIR, "muhl_esnr.mno")


class TestReadIsVoltage(unittest.TestCase):
    def test_button_is_read_only_and_resolves_stored_ones(self):
        paths = list_excerpts(EXCERPT_DIR)
        self.assertGreaterEqual(len(paths), 19, "PLUMB 1-19 excerpts missing")
        data = read_census(paths)
        self.assertEqual(data["host_writes"], 0)
        self.assertEqual(data["host_mode"], "READ")
        self.assertIs(data["second_write_required"], False)
        self.assertEqual(data["titan"], "NOT_WRITTEN")
        self.assertEqual(data["const1_written"], data["excerpts"])
        self.assertGreaterEqual(data["read_of_stored_1"], 16)
        for row in data["rows"]:
            self.assertEqual(row["host_writes"], 0, row["path"])
            self.assertEqual(row["host_mode"], "READ", row["path"])
            self.assertEqual(row["const1_written"], 1, row["path"])
            self.assertEqual(row["read_of_stored_1"], row["share1"], row["path"])

    def test_lvin_read_of_one_stored_one_feeds_1901_gates(self):
        self.assertTrue(os.path.isfile(LVIN), "muhl_lvin.mno missing")
        row = read_only_row(LVIN)
        self.assertEqual(row["host_writes"], 0)
        self.assertEqual(row["const1_addr"], 541)
        self.assertEqual(row["const1_written"], 1)
        self.assertEqual(row["read_of_stored_1"], 1901)
        self.assertIs(row["second_write_required"], False)

    def test_esnr_read_fan_in_stays_on_the_stored_charge(self):
        row = read_only_row(ESNR)
        self.assertEqual(row["host_writes"], 0)
        self.assertEqual(row["read_of_stored_1"], 4132)
        self.assertEqual(row["titan"], "NOT_WRITTEN")


if __name__ == "__main__":
    unittest.main()
