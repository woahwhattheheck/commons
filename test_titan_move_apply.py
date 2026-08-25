#!/usr/bin/env python3
"""Titan MOVE apply is a plan here. It does not write titan.gguf."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from titan_move_apply import apply_journal, journal_rows, main, plan_from_packet
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

    def test_journal_or_writes_and_rereads(self):
        with tempfile.TemporaryDirectory() as tmp:
            excerpt_dir = os.path.join(tmp, "ex")
            os.makedirs(excerpt_dir)
            with open(os.path.join(excerpt_dir, "a.mno"), "wb") as handle:
                handle.write(b"\x01\x00")
            with open(os.path.join(excerpt_dir, "b.mno"), "wb") as handle:
                handle.write(b"\x02\x01")
            rows, end = journal_rows([
                {"name": "a", "container": "a.mno", "len": 2, "offset": 9},
                {"name": "b", "container": "b.mno", "len": 2, "offset": 11},
            ])
            self.assertEqual(end, 4)
            self.assertEqual(rows[0]["journal_offset"], 0)
            self.assertEqual(rows[0]["claimed_titan_offset"], 9)
            image = os.path.join(tmp, "journal.bin")
            journals = apply_journal(image, rows, excerpt_dir)
            self.assertEqual(len(journals), 2)
            self.assertTrue(all(row["reread"] for row in journals))
            with open(image, "rb") as handle:
                self.assertEqual(handle.read(), b"\x01\x00\x02\x01")

    def test_journal_flag_lands_sidecar(self):
        self.assertEqual(main(["--root", ROOT, "--journal"]), 0)
        sidecar = os.path.join(ROOT, "excerpts", "20260823", "titan_move_journal.json")
        self.assertTrue(os.path.isfile(sidecar))
        with open(sidecar, encoding="utf-8") as handle:
            payload = json.load(handle)
        self.assertEqual(payload["count"], 31)
        self.assertTrue(payload["reread"])
        self.assertEqual(len(payload["organs"]), 31)
        self.assertTrue(all(row["reread"] for row in payload["organs"]))


if __name__ == "__main__":
    unittest.main()
