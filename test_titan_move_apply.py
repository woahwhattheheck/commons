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

from titan_append_guard import INCIDENT_BASE, INCIDENT_FIRST_END, INCIDENT_LIVE_SIZE, INCIDENT_PAYLOAD
from titan_move_apply import (
    already_applied,
    apply_journal,
    journal_rows,
    main,
    persist_write_facts,
    plan_from_packet,
)
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

    def test_already_applied_when_live_size_equals_end(self):
        packet = {
            "titan": "WRITTEN",
            "claimed_append_base": 10,
            "claimed_append_end": 14,
            "count": 1,
            "organs": [{"name": "a", "len": 4}],
        }
        self.assertTrue(already_applied(packet, 14))
        self.assertFalse(already_applied(packet, 10))
        self.assertFalse(already_applied(packet, None))
        plan = plan_from_packet(packet, live_size=14)
        self.assertFalse(plan["reallocated"])
        self.assertEqual(plan["claimed_append_base"], 10)

    def test_persist_write_facts_counts_and_sizes(self):
        packet = persist_write_facts(
            {
                "titan": "NOT_WRITTEN",
                "organs": [{"name": "a", "titan": "NOT_WRITTEN"}],
            },
            write_count=31,
            reread_count=31,
            live_size_before=103803350291,
            live_size_after=103812669582,
        )
        self.assertEqual(packet["titan"], "WRITTEN")
        self.assertTrue(packet["reread"])
        self.assertEqual(packet["write_count"], 31)
        self.assertEqual(packet["reread_count"], 31)
        self.assertEqual(packet["written_bytes"], 9319291)
        self.assertEqual(packet["organs"][0]["titan"], "WRITTEN")

    def test_plan_does_not_reallocate_incident_size(self):
        packet = {
            "titan": "WRITTEN",
            "claimed_append_base": INCIDENT_BASE,
            "claimed_append_end": INCIDENT_FIRST_END,
            "written_bytes": INCIDENT_PAYLOAD,
            "organs": [{"name": "a", "len": INCIDENT_PAYLOAD, "container": "a.mno"}],
        }
        plan = plan_from_packet(packet, live_size=INCIDENT_LIVE_SIZE)
        self.assertTrue(plan["refused"])
        self.assertFalse(plan["reallocated"])
        self.assertEqual(plan["claimed_append_base"], INCIDENT_BASE)

    def test_go_fail_closes_against_duplicate_append(self):
        with tempfile.TemporaryDirectory() as tmp:
            excerpt_dir = os.path.join(tmp, "excerpts", "20260823")
            os.makedirs(excerpt_dir)
            with open(os.path.join(excerpt_dir, "a.mno"), "wb") as handle:
                handle.write(b"ab")
            packet = {
                "kind": "TITAN_MOVE_PACKET",
                "titan": "WRITTEN",
                "reread": True,
                "write_count": 1,
                "reread_count": 1,
                "claimed_append_base": 2,
                "claimed_append_end": 4,
                "count": 1,
                "organs": [
                    {
                        "name": "a",
                        "container": "a.mno",
                        "len": 2,
                        "offset": 2,
                        "titan": "WRITTEN",
                    }
                ],
            }
            packet_path = os.path.join(excerpt_dir, "titan_move_packet.json")
            with open(packet_path, "w", encoding="utf-8") as handle:
                json.dump(packet, handle)
            titan = os.path.join(tmp, "titan.gguf")
            with open(titan, "wb") as handle:
                handle.write(b"xxab")
            before = os.path.getsize(titan)
            self.assertEqual(
                main(["--root", tmp, "--titan", titan, "--go"]),
                0,
            )
            self.assertEqual(os.path.getsize(titan), before)
            with open(packet_path, encoding="utf-8") as handle:
                landed = json.load(handle)
            self.assertEqual(landed["titan"], "WRITTEN")
            self.assertTrue(landed["reread"])
            self.assertEqual(landed["live_size_after"], before)

    def test_go_fail_closes_incident_size_without_rewriting_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            excerpt_dir = os.path.join(tmp, "excerpts", "20260823")
            os.makedirs(excerpt_dir)
            with open(os.path.join(excerpt_dir, "a.mno"), "wb") as handle:
                handle.write(b"ab")
            packet = {
                "kind": "TITAN_MOVE_PACKET",
                "titan": "WRITTEN",
                "reread": True,
                "write_count": 1,
                "reread_count": 1,
                "claimed_append_base": INCIDENT_BASE,
                "claimed_append_end": INCIDENT_FIRST_END,
                "written_bytes": INCIDENT_PAYLOAD,
                "count": 1,
                "organs": [
                    {
                        "name": "a",
                        "container": "a.mno",
                        "len": 2,
                        "offset": INCIDENT_BASE,
                        "titan": "WRITTEN",
                    }
                ],
            }
            packet_path = os.path.join(excerpt_dir, "titan_move_packet.json")
            with open(packet_path, "w", encoding="utf-8") as handle:
                json.dump(packet, handle)
            titan = os.path.join(tmp, "titan.gguf")
            with open(titan, "wb") as handle:
                handle.write(b"xxabxxabxxab")
            self.assertEqual(
                main(["--root", tmp, "--titan", titan, "--go"]),
                0,
            )
            with open(packet_path, encoding="utf-8") as handle:
                landed = json.load(handle)
            self.assertEqual(landed["claimed_append_end"], INCIDENT_FIRST_END)
            self.assertEqual(os.path.getsize(titan), 12)

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
