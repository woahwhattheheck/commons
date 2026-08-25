#!/usr/bin/env python3
"""Titan MOVE apply is a plan here. It does not write titan.gguf."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from titan_move_apply import main, plan_from_packet
from titan_move_offsets import (
    CLAIMED_APPEND_BASE,
    allocate_rows,
    find_titan,
    or_bytes,
)


class TestTitanMoveOffsets(unittest.TestCase):
    def test_or_bytes_ones_only_rise(self):
        self.assertEqual(or_bytes(b"\x01\x00", b"\x02\x01"), b"\x03\x01")
        self.assertEqual(or_bytes(b"", b"\xff"), b"\xff")
        self.assertEqual(or_bytes(b"\xff", b"\x00"), b"\xff")

    def test_allocate_from_dest_file_base(self):
        rows = [{"name": "a", "len": 10}, {"name": "b", "len": 5}]
        allocated, end = allocate_rows(rows, base=CLAIMED_APPEND_BASE)
        self.assertEqual(allocated[0]["offset"], CLAIMED_APPEND_BASE)
        self.assertEqual(allocated[1]["offset"], CLAIMED_APPEND_BASE + 10)
        self.assertEqual(end, CLAIMED_APPEND_BASE + 15)
        self.assertIn("CLAIMED_APPEND", allocated[0]["requested_offset_band"])

    def test_find_titan_skips_commons_mno(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = os.path.join(tmp, "commons.mno")
            with open(fake, "wb") as handle:
                handle.write(b"no")
            self.assertIsNone(find_titan(explicit=fake))

    def test_plan_reallocates_when_live_size_differs(self):
        packet = {
            "claimed_append_base": CLAIMED_APPEND_BASE,
            "organs": [{"name": "a", "len": 8, "container": "a.mno"}],
        }
        plan = plan_from_packet(packet, live_size=CLAIMED_APPEND_BASE + 100)
        self.assertTrue(plan["reallocated"])
        self.assertEqual(plan["claimed_append_base"], CLAIMED_APPEND_BASE + 100)
        self.assertEqual(plan["organs"][0]["offset"], CLAIMED_APPEND_BASE + 100)

    def test_plan_only_does_not_write(self):
        self.assertEqual(main(["--root", ROOT]), 0)

    def test_go_without_titan_is_absent(self):
        self.assertEqual(main(["--root", ROOT, "--go"]), 2)

    def test_inject_is_refused(self):
        self.assertEqual(main(["--inject", "0x01"]), 2)


if __name__ == "__main__":
    unittest.main()
