#!/usr/bin/env python3
"""Titan MOVE contract tests, including legitimate live owner actuation."""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from titan_move_apply import (
    apply_journal,
    journal_rows,
    main,
    plan_from_packet,
    write_json,
)
from titan_move_offsets import (
    CLAIMED_APPEND_BASE,
    allocate_rows,
    find_titan,
    or_bytes,
)


def run_json_main(argv):
    """Run the CLI entrypoint and decode the JSON before its DIE marker."""
    output = io.StringIO()
    with redirect_stdout(output):
        rc = main(argv)
    body = output.getvalue().rsplit("\nDIE", 1)[0]
    return rc, json.loads(body)


class TestTitanMoveOffsets(unittest.TestCase):
    def test_live_receipts_are_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "before-after.json")
            write_json(path, {"reread": True}, exclusive=True)
            with self.assertRaises(FileExistsError):
                write_json(path, {"reread": False}, exclusive=True)

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

    def test_find_titan_rejects_commons_mno_and_falls_through_to_owner_titan(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = os.path.join(tmp, "commons.mno")
            with open(fake, "wb") as handle:
                handle.write(b"no")
            found = find_titan(explicit=fake)
            default = os.path.abspath(r"C:\llm\models\titan.gguf")
            if os.path.isfile(default):
                self.assertEqual(os.path.normcase(found), os.path.normcase(default))
            else:
                self.assertIsNone(found)

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
        titan = find_titan()
        before = os.path.getsize(titan) if titan else None
        rc, payload = run_json_main(["--root", ROOT])
        after = os.path.getsize(titan) if titan else None
        self.assertEqual(rc, 0)
        self.assertFalse(payload["go"])
        self.assertFalse(payload["wrote"])
        self.assertEqual(after, before)

    def test_go_actuates_live_owner_titan_and_persists_reread_receipt(self):
        titan = find_titan()
        if not titan:
            self.skipTest("live owner titan.gguf is not on this computer")
        with open(
            os.path.join(ROOT, "excerpts", "20260823", "titan_move_packet.json"),
            encoding="utf-8",
        ) as handle:
            packet_before = json.load(handle)
        expected_bytes = sum(int(row["len"]) for row in packet_before["organs"])
        before = os.path.getsize(titan)
        rc, payload = run_json_main(
            ["--root", ROOT, "--titan", titan, "--go"]
        )
        after = os.path.getsize(titan)
        self.assertEqual(rc, 0)
        self.assertTrue(payload["wrote"])
        self.assertTrue(payload["reread"])
        self.assertEqual(payload["state"], "INTEGRATED")
        self.assertEqual(payload["before_size"], before)
        self.assertEqual(payload["after_size"], after)
        self.assertEqual(payload["bytes_added"], expected_bytes)
        self.assertEqual(after - before, expected_bytes)
        self.assertEqual(payload["plan"]["claimed_append_base"], before)
        self.assertEqual(payload["plan"]["claimed_append_end"], after)
        self.assertEqual(len(payload["journals"]), 31)
        self.assertTrue(all(row["reread"] for row in payload["journals"]))
        self.assertTrue(all(row["past_eof"] for row in payload["journals"]))
        self.assertEqual(payload["journals"][0]["offset"], before)
        last = payload["journals"][-1]
        self.assertEqual(last["offset"] + last["len"], after)

        with open(titan, "rb") as handle:
            for row in payload["journals"]:
                handle.seek(row["offset"])
                reread = handle.read(row["len"])
                self.assertEqual(hashlib.sha256(reread).hexdigest(), row["new_sha256"])

        receipt_path = os.path.join(
            ROOT, payload["live_receipt_path"].replace("/", os.sep)
        )
        self.assertTrue(os.path.isfile(receipt_path))
        with open(receipt_path, encoding="utf-8") as handle:
            receipt = json.load(handle)
        self.assertEqual(receipt["before_size"], before)
        self.assertEqual(receipt["after_size"], after)
        self.assertEqual(receipt["bytes_added"], expected_bytes)
        self.assertTrue(receipt["reread"])
        self.assertEqual(receipt["organs"], payload["journals"])

        with open(
            os.path.join(ROOT, "excerpts", "20260823", "titan_move_packet.json"),
            encoding="utf-8",
        ) as handle:
            packet_after = json.load(handle)
        self.assertEqual(packet_after["titan"], "WRITTEN")
        self.assertEqual(packet_after["claimed_append_base"], before)
        self.assertEqual(packet_after["claimed_append_end"], after)
        self.assertEqual(packet_after["last_live_receipt"], payload["live_receipt_path"])
        self.assertTrue(packet_after["reread"])

    def test_inject_is_refused(self):
        output = io.StringIO()
        with redirect_stdout(output):
            rc = main(["--inject", "0x01"])
        self.assertEqual(rc, 2)

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
        rc, output = run_json_main(["--root", ROOT, "--journal"])
        self.assertEqual(rc, 0)
        self.assertTrue(output["reread"])
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
