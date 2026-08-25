#!/usr/bin/env python3
"""Titan MOVE apply is a plan here. It does not write titan.gguf."""
from __future__ import annotations

import json
import hashlib
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from titan_append_guard import INCIDENT_BASE, INCIDENT_FIRST_END, INCIDENT_LIVE_SIZE, INCIDENT_PAYLOAD
from titan_move_apply import (
    apply_journal,
    journal_rows,
    main,
    plan_from_packet,
    scan_repeated_append_spans,
    verify_written_packet,
    write_and_incident_evidence_complete,
)
from titan_move_offsets import (
    CLAIMED_APPEND_BASE,
    TEST_ISOLATE_ENV,
    allocate_rows,
    find_titan,
    is_owner_titan_path,
    or_bytes,
    under_test,
)
import titan_move_offsets

os.environ[TEST_ISOLATE_ENV] = "1"


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

    def test_under_test_is_isolated(self):
        self.assertEqual(os.environ.get(TEST_ISOLATE_ENV), "1")
        self.assertTrue(under_test())
        self.assertTrue(is_owner_titan_path(r"C:\llm\models\titan.gguf"))
        self.assertTrue(is_owner_titan_path("/llm/models/titan.gguf"))
        self.assertFalse(is_owner_titan_path("/tmp/synth-titan.gguf"))

    def test_find_titan_under_test_skips_dest_from_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_live = os.path.join(tmp, "titan.gguf")
            with open(fake_live, "wb") as handle:
                handle.write(b"LIVE")
            old = titan_move_offsets.TITAN_DEST_FROM_FILE
            try:
                titan_move_offsets.TITAN_DEST_FROM_FILE = fake_live
                self.assertIsNone(find_titan())
                self.assertIsNone(find_titan(explicit=fake_live))
                self.assertIsNone(find_titan(env_path=fake_live))
                synth = os.path.join(tmp, "synth.gguf")
                with open(synth, "wb") as handle:
                    handle.write(b"SYNTH")
                self.assertEqual(find_titan(explicit=synth), synth)
            finally:
                titan_move_offsets.TITAN_DEST_FROM_FILE = old

    def test_plan_reallocates_when_live_size_differs(self):
        packet = {
            "claimed_append_base": CLAIMED_APPEND_BASE,
            "organs": [{"name": "a", "len": 8, "container": "a.mno"}],
        }
        plan = plan_from_packet(packet, live_size=CLAIMED_APPEND_BASE + 100)
        self.assertTrue(plan["reallocated"])
        self.assertEqual(plan["claimed_append_base"], CLAIMED_APPEND_BASE + 100)
        self.assertEqual(plan["organs"][0]["offset"], CLAIMED_APPEND_BASE + 100)

    def test_persisted_completion_requires_structural_organs(self):
        fake = {
            "titan": "WRITTEN",
            "state": "INTEGRATED",
            "wrote": True,
            "reread": True,
            "count": 1,
            "reread_count": 1,
            "past_eof_count": 1,
            "claimed_append_base": 4,
            "claimed_append_end": 5,
            "titan_size_before": 4,
            "titan_size_after": 5,
            "written_bytes": 1,
            "write_receipt": "p/fake.md",
            "integrated_commit": "1" * 40,
            "organs": [],
        }
        self.assertFalse(write_and_incident_evidence_complete(fake, root=ROOT))

    def test_persisted_completion_requires_receipt_body_on_same_tree(self):
        packet_path = os.path.join(
            ROOT, "excerpts", "20260823", "titan_move_packet.json"
        )
        with open(packet_path, encoding="utf-8") as handle:
            packet = json.load(handle)
        self.assertTrue(write_and_incident_evidence_complete(packet, root=ROOT))
        damaged = json.loads(json.dumps(packet))
        damaged["organs"][1]["offset"] = damaged["organs"][0]["offset"]
        self.assertFalse(write_and_incident_evidence_complete(damaged, root=ROOT))
        damaged = json.loads(json.dumps(packet))
        damaged["organs"][0]["sha256"] = "0" * 64
        self.assertFalse(write_and_incident_evidence_complete(damaged, root=ROOT))
        damaged = json.loads(json.dumps(packet))
        damaged["organs"][1]["container"] = damaged["organs"][0]["container"]
        self.assertFalse(write_and_incident_evidence_complete(damaged, root=ROOT))
        damaged = json.loads(json.dumps(packet))
        damaged["organs"][0]["container"] = (
            "./" + damaged["organs"][0]["container"]
        )
        self.assertFalse(write_and_incident_evidence_complete(damaged, root=ROOT))
        damaged = json.loads(json.dumps(packet))
        damaged["duplicate_append_incident"]["span_count"] = "FINDER-FAILED"
        self.assertFalse(write_and_incident_evidence_complete(damaged, root=ROOT))
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(write_and_incident_evidence_complete(packet, root=tmp))
            receipt_path = os.path.join(
                tmp, "p", "claudelocal-titan-move-go-20260825-01.md"
            )
            os.makedirs(os.path.dirname(receipt_path))
            with open(receipt_path, "w", encoding="utf-8") as handle:
                handle.write("fake exact-looking path without owner evidence\n")
            self.assertFalse(write_and_incident_evidence_complete(packet, root=tmp))

    def test_plan_only_reports_paused_live_incident_without_write(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(["--root", ROOT]), 0)
        self.assertIn('"state": "NOT_LANDED"', out.getvalue())
        self.assertIn("duplicate appends", out.getvalue())
        self.assertIn("PAUSED", out.getvalue())

    def test_go_with_synthetic_titan_keeps_incident_paused_without_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            titan = os.path.join(tmp, "synthetic.gguf")
            with open(titan, "wb") as handle:
                handle.write(b"GGUF")
            with open(titan, "rb") as handle:
                before = handle.read()
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(
                    main(["--root", ROOT, "--titan", titan, "--go"]),
                    2,
                )
            with open(titan, "rb") as handle:
                self.assertEqual(handle.read(), before)
        self.assertIn('"already_written": true', out.getvalue())
        self.assertIn("incident remains PAUSED", out.getvalue())

    def test_inject_is_refused(self):
        self.assertEqual(main(["--inject", "0x01"]), 2)

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

    def test_default_discovery_stays_absent_even_if_dest_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_live = os.path.join(tmp, "titan.gguf")
            with open(fake_live, "wb") as handle:
                handle.write(b"LIVE")
            old = titan_move_offsets.TITAN_DEST_FROM_FILE
            try:
                titan_move_offsets.TITAN_DEST_FROM_FILE = fake_live
                self.assertIsNone(find_titan())
            finally:
                titan_move_offsets.TITAN_DEST_FROM_FILE = old

    def test_go_first_write_then_written_reread_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            excerpt_dir = os.path.join(tmp, "excerpts", "20260823")
            os.makedirs(excerpt_dir)
            organ = b"ab"
            with open(os.path.join(excerpt_dir, "a.mno"), "wb") as handle:
                handle.write(organ)
            packet = {
                "kind": "TITAN_MOVE_PACKET",
                "titan": "NOT_WRITTEN",
                "claimed_append_base": 4,
                "claimed_append_end": 6,
                "count": 1,
                "organs": [
                    {
                        "name": "a",
                        "container": "a.mno",
                        "len": 2,
                        "offset": 4,
                        "sha256": hashlib.sha256(organ).hexdigest(),
                    }
                ],
            }
            packet_path = os.path.join(excerpt_dir, "titan_move_packet.json")
            with open(packet_path, "w", encoding="utf-8") as handle:
                json.dump(packet, handle)
            titan = os.path.join(tmp, "synth.gguf")
            with open(titan, "wb") as handle:
                handle.write(b"GGUF")
            self.assertEqual(main(["--root", tmp, "--titan", titan, "--go"]), 0)
            with open(titan, "rb") as handle:
                titan_after_first = handle.read()
            with open(packet_path, "rb") as handle:
                packet_after_first = handle.read()
            landed = json.loads(packet_after_first)
            self.assertEqual(landed["titan"], "WRITTEN")
            self.assertEqual(main(["--root", tmp, "--titan", titan, "--go"]), 0)
            with open(titan, "rb") as handle:
                self.assertEqual(handle.read(), titan_after_first)
            with open(packet_path, "rb") as handle:
                self.assertEqual(handle.read(), packet_after_first)

    def test_go_fail_closes_against_duplicate_append(self):
        with tempfile.TemporaryDirectory() as tmp:
            excerpt_dir = os.path.join(tmp, "excerpts", "20260823")
            os.makedirs(excerpt_dir)
            organ = b"ab"
            with open(os.path.join(excerpt_dir, "a.mno"), "wb") as handle:
                handle.write(organ)
            packet = {
                "kind": "TITAN_MOVE_PACKET",
                "titan": "WRITTEN",
                "reread": True,
                "write_count": 1,
                "reread_count": 1,
                "claimed_append_base": 4,
                "claimed_append_end": 6,
                "count": 1,
                "organs": [
                    {
                        "name": "a",
                        "container": "a.mno",
                        "len": 2,
                        "offset": 4,
                        "sha256": hashlib.sha256(organ).hexdigest(),
                        "titan": "WRITTEN",
                    }
                ],
            }
            packet_path = os.path.join(excerpt_dir, "titan_move_packet.json")
            with open(packet_path, "w", encoding="utf-8") as handle:
                json.dump(packet, handle)
            titan = os.path.join(tmp, "titan.gguf")
            with open(titan, "wb") as handle:
                handle.write(b"GGUF" + organ)
            with open(packet_path, "rb") as handle:
                packet_before = handle.read()
            titan_before = os.path.getsize(titan)
            self.assertEqual(
                main(["--root", tmp, "--titan", titan, "--go"]),
                0,
            )
            self.assertEqual(os.path.getsize(titan), titan_before)
            with open(packet_path, "rb") as handle:
                self.assertEqual(handle.read(), packet_before)

    def test_go_fail_closes_incident_size_without_rewriting_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            excerpt_dir = os.path.join(tmp, "excerpts", "20260823")
            os.makedirs(excerpt_dir)
            organ = b"ab"
            with open(os.path.join(excerpt_dir, "a.mno"), "wb") as handle:
                handle.write(organ)
            packet = {
                "kind": "TITAN_MOVE_PACKET",
                "titan": "WRITTEN",
                "reread": True,
                "write_count": 1,
                "reread_count": 1,
                "claimed_append_base": 4,
                "claimed_append_end": 6,
                "written_bytes": 2,
                "count": 1,
                "duplicate_append_incident": {
                    "state": "PAUSED_DUPLICATE_APPENDS"
                },
                "organs": [
                    {
                        "name": "a",
                        "container": "a.mno",
                        "len": 2,
                        "offset": 4,
                        "sha256": hashlib.sha256(organ).hexdigest(),
                        "titan": "WRITTEN",
                    }
                ],
            }
            packet_path = os.path.join(excerpt_dir, "titan_move_packet.json")
            with open(packet_path, "w", encoding="utf-8") as handle:
                json.dump(packet, handle)
            titan = os.path.join(tmp, "titan.gguf")
            with open(titan, "wb") as handle:
                handle.write(b"GGUF" + organ * 3)
            with open(packet_path, "rb") as handle:
                packet_before = handle.read()
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(
                    main(["--root", tmp, "--titan", titan, "--go"]),
                    2,
                )
            self.assertIn('"state": "NOT_LANDED"', out.getvalue())
            self.assertIn('"duplicate_span_count": 2', out.getvalue())
            with open(packet_path, "rb") as handle:
                self.assertEqual(handle.read(), packet_before)
            self.assertEqual(os.path.getsize(titan), 10)

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
        with tempfile.TemporaryDirectory() as tmp:
            excerpt_dir = os.path.join(tmp, "excerpts", "20260823")
            os.makedirs(excerpt_dir)
            organ = b"\x01\x00"
            with open(os.path.join(excerpt_dir, "one.mno"), "wb") as handle:
                handle.write(organ)
            packet = {
                "kind": "TITAN_MOVE_PACKET",
                "titan": "NOT_WRITTEN",
                "count": 1,
                "claimed_append_base": 9,
                "organs": [{
                    "name": "one",
                    "container": "one.mno",
                    "len": len(organ),
                    "offset": 9,
                    "sha256": hashlib.sha256(organ).hexdigest(),
                }],
            }
            with open(os.path.join(excerpt_dir, "titan_move_packet.json"), "w") as handle:
                json.dump(packet, handle)
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(["--root", tmp, "--journal"]), 0)
            sidecar = os.path.join(excerpt_dir, "titan_move_journal.json")
            self.assertTrue(os.path.isfile(sidecar))
            with open(sidecar, encoding="utf-8") as handle:
                payload = json.load(handle)
            self.assertEqual(payload["count"], 1)
            self.assertTrue(payload["reread"])
            self.assertEqual(len(payload["organs"]), 1)
            self.assertTrue(all(row["reread"] for row in payload["organs"]))

    def test_verify_written_packet_rereads_exact_spans(self):
        with tempfile.TemporaryDirectory() as tmp:
            titan = os.path.join(tmp, "titan.gguf")
            one, two = b"first organ", b"second organ"
            with open(titan, "wb") as handle:
                handle.write(b"GGUF" + one + two)
            packet = {
                "count": 2,
                "titan_size_before": 4,
                "claimed_append_base": 4,
                "claimed_append_end": 4 + len(one) + len(two),
                "organs": [
                    {
                        "name": "one",
                        "container": "one.mno",
                        "offset": 4,
                        "len": len(one),
                        "sha256": hashlib.sha256(one).hexdigest(),
                    },
                    {
                        "name": "two",
                        "container": "two.mno",
                        "offset": 4 + len(one),
                        "len": len(two),
                        "sha256": hashlib.sha256(two).hexdigest(),
                    },
                ],
            }
            measured = verify_written_packet(titan, packet)
            self.assertTrue(measured["reread"])
            self.assertEqual(measured["exact_count"], 2)
            self.assertTrue(all(row["past_eof"] for row in measured["organs"]))

            duplicate = json.loads(json.dumps(packet))
            duplicate["organs"][1]["container"] = "one.mno"
            measured = verify_written_packet(titan, duplicate)
            self.assertFalse(measured["reread"])
            self.assertFalse(measured["geometry_complete"])

            nonbasename = json.loads(json.dumps(packet))
            nonbasename["organs"][0]["container"] = "nested/one.mno"
            measured = verify_written_packet(titan, nonbasename)
            self.assertFalse(measured["reread"])
            self.assertFalse(measured["geometry_complete"])

            with open(titan, "r+b") as handle:
                handle.seek(4)
                handle.write(b"X")
            measured = verify_written_packet(titan, packet)
            self.assertFalse(measured["reread"])
            self.assertEqual(measured["exact_count"], 1)

    def test_written_go_is_idempotent_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet_dir = os.path.join(tmp, "excerpts", "20260823")
            os.makedirs(packet_dir)
            titan = os.path.join(tmp, "titan.gguf")
            organ = b"already appended"
            with open(titan, "wb") as handle:
                handle.write(b"GGUF" + organ)
            packet = {
                "kind": "TITAN_MOVE_PACKET",
                "titan": "WRITTEN",
                "count": 1,
                "claimed_append_base": 4,
                "claimed_append_end": 4 + len(organ),
                "titan_size_before": 4,
                "organs": [{
                    "name": "one",
                    "container": "one.mno",
                    "offset": 4,
                    "len": len(organ),
                    "sha256": hashlib.sha256(organ).hexdigest(),
                }],
            }
            with open(os.path.join(packet_dir, "titan_move_packet.json"), "w") as handle:
                json.dump(packet, handle)
            before_size = os.path.getsize(titan)
            with open(titan, "rb") as handle:
                before_sha = hashlib.sha256(handle.read()).hexdigest()
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--root", tmp, "--titan", titan, "--go"])
            self.assertEqual(code, 0, out.getvalue())
            self.assertIn('"already_written": true', out.getvalue())
            self.assertIn("No allocation and no write", out.getvalue())
            self.assertEqual(os.path.getsize(titan), before_size)
            with open(titan, "rb") as handle:
                after_sha = hashlib.sha256(handle.read()).hexdigest()
            self.assertEqual(after_sha, before_sha)

    def test_written_go_detects_three_identical_spans_without_fourth_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet_dir = os.path.join(tmp, "excerpts", "20260823")
            os.makedirs(packet_dir)
            titan = os.path.join(tmp, "titan.gguf")
            organ = b"known present append payload"
            with open(titan, "wb") as handle:
                handle.write(b"GGUF" + organ + organ + organ)
            packet = {
                "kind": "TITAN_MOVE_PACKET",
                "titan": "WRITTEN",
                "count": 1,
                "claimed_append_base": 4,
                "claimed_append_end": 4 + len(organ),
                "titan_size_before": 4,
                "organs": [{
                    "name": "one",
                    "container": "one.mno",
                    "offset": 4,
                    "len": len(organ),
                    "sha256": hashlib.sha256(organ).hexdigest(),
                }],
            }
            with open(
                os.path.join(packet_dir, "titan_move_packet.json"), "w"
            ) as handle:
                json.dump(packet, handle)
            with open(titan, "rb") as handle:
                before = handle.read()
            measured = verify_written_packet(titan, packet)
            scan = measured["repeated_span_scan"]
            self.assertTrue(measured["reread"])
            self.assertTrue(measured["duplicate_append_incident"])
            self.assertEqual(measured["duplicate_span_count"], 2)
            self.assertEqual(scan["state"], "MEASURED")
            self.assertEqual(scan["full_span_count"], 3)
            self.assertEqual(scan["scanned_span_count"], 3)
            self.assertTrue(scan["scan_complete"])
            self.assertTrue(scan["calibration_ok"])
            self.assertEqual(scan["search_start"], 4)
            self.assertEqual(scan["search_end"], 4 + 3 * len(organ))
            self.assertEqual(len(set(scan["span_sha256"])), 1)
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--root", tmp, "--titan", titan, "--go"])
            self.assertEqual(code, 2, out.getvalue())
            self.assertIn("2 byte-identical duplicate", out.getvalue())
            self.assertIn("No allocation and no write", out.getvalue())
            with open(titan, "rb") as handle:
                self.assertEqual(handle.read(), before)

    def test_repeated_span_scan_never_turns_bounded_miss_into_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet_dir = os.path.join(tmp, "excerpts", "20260823")
            os.makedirs(packet_dir)
            titan = os.path.join(tmp, "titan.gguf")
            organ = b"calibration"
            with open(titan, "wb") as handle:
                handle.write(b"GGUF" + organ * 17)
            packet = {
                "kind": "TITAN_MOVE_PACKET",
                "titan": "WRITTEN",
                "count": 1,
                "claimed_append_base": 4,
                "claimed_append_end": 4 + len(organ),
                "titan_size_before": 4,
                "organs": [{
                    "name": "one",
                    "container": "one.mno",
                    "offset": 4,
                    "len": len(organ),
                    "sha256": hashlib.sha256(organ).hexdigest(),
                }],
            }
            with open(
                os.path.join(packet_dir, "titan_move_packet.json"), "w"
            ) as handle:
                json.dump(packet, handle)
            measured = verify_written_packet(titan, packet)
            scan = measured["repeated_span_scan"]
            self.assertEqual(scan["state"], "FINDER-FAILED")
            self.assertEqual(scan["full_span_count"], 17)
            self.assertEqual(scan["scanned_span_count"], 16)
            self.assertFalse(scan["scan_complete"])
            self.assertFalse(scan["duplicate_count_complete"])
            self.assertEqual(scan["search_start"], 4)
            self.assertEqual(scan["search_end"], 4 + 17 * len(organ))
            uncalibrated = scan_repeated_append_spans(
                titan, 4, 4 + len(organ), calibrated=False
            )
            self.assertEqual(uncalibrated["state"], "FINDER-FAILED")
            self.assertIsNone(uncalibrated["duplicate_span_count"])
            with open(titan, "rb") as handle:
                before = handle.read()
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--root", tmp, "--titan", titan, "--go"])
            self.assertEqual(code, 2, out.getvalue())
            self.assertIn("FINDER-FAILED", out.getvalue())
            with open(titan, "rb") as handle:
                self.assertEqual(handle.read(), before)

    def test_written_go_mismatch_fails_closed_without_append(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet_dir = os.path.join(tmp, "excerpts", "20260823")
            os.makedirs(packet_dir)
            titan = os.path.join(tmp, "titan.gguf")
            organ = b"actual bytes"
            with open(titan, "wb") as handle:
                handle.write(b"GGUF" + organ)
            packet = {
                "kind": "TITAN_MOVE_PACKET",
                "titan": "WRITTEN",
                "count": 1,
                "claimed_append_base": 4,
                "claimed_append_end": 4 + len(organ),
                "titan_size_before": 4,
                "organs": [{
                    "name": "one",
                    "container": "one.mno",
                    "offset": 4,
                    "len": len(organ),
                    "sha256": hashlib.sha256(b"different").hexdigest(),
                }],
            }
            with open(os.path.join(packet_dir, "titan_move_packet.json"), "w") as handle:
                json.dump(packet, handle)
            before_size = os.path.getsize(titan)
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--root", tmp, "--titan", titan, "--go"])
            self.assertEqual(code, 2, out.getvalue())
            self.assertIn('"state": "NOT_LANDED"', out.getvalue())
            self.assertEqual(os.path.getsize(titan), before_size)

    def test_first_go_persists_execution_truth(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet_dir = os.path.join(tmp, "excerpts", "20260823")
            os.makedirs(packet_dir)
            titan = os.path.join(tmp, "titan.gguf")
            organ = b"new organ"
            with open(titan, "wb") as handle:
                handle.write(b"GGUF")
            with open(os.path.join(packet_dir, "one.mno"), "wb") as handle:
                handle.write(organ)
            packet = {
                "kind": "TITAN_MOVE_PACKET",
                "titan": "NOT_WRITTEN",
                "count": 1,
                "claimed_append_base": 4,
                "organs": [{
                    "name": "one",
                    "container": "one.mno",
                    "len": len(organ),
                    "sha256": hashlib.sha256(organ).hexdigest(),
                }],
            }
            packet_path = os.path.join(packet_dir, "titan_move_packet.json")
            with open(packet_path, "w") as handle:
                json.dump(packet, handle)
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--root", tmp, "--titan", titan, "--go"])
            self.assertEqual(code, 0, out.getvalue())
            with open(packet_path) as handle:
                landed = json.load(handle)
            self.assertEqual(landed["state"], "WRITTEN")
            self.assertTrue(landed["wrote"])
            self.assertTrue(landed["reread"])
            self.assertEqual(landed["write_count"], 1)
            self.assertFalse(write_and_incident_evidence_complete(landed, root=tmp))
            self.assertIn('"state": "NOT_LANDED"', out.getvalue())
            self.assertEqual(landed["reread_count"], 1)
            self.assertEqual(landed["past_eof_count"], 1)
            self.assertEqual(landed["titan_size_before"], 4)
            self.assertEqual(landed["titan_size_after"], 4 + len(organ))
            self.assertEqual(landed["live_size_before"], 4)
            self.assertEqual(landed["live_size_after"], 4 + len(organ))
            self.assertEqual(landed["written_bytes"], len(organ))
            self.assertEqual(
                landed["organs"][0]["written_sha256"],
                hashlib.sha256(organ).hexdigest(),
            )
            self.assertEqual(landed["organs"][0]["pre_len"], 0)
            self.assertEqual(
                landed["organs"][0]["pre_sha256"],
                hashlib.sha256(b"").hexdigest(),
            )
            with open(titan, "rb") as handle:
                written_once = handle.read()
            reread_out = io.StringIO()
            with redirect_stdout(reread_out):
                self.assertEqual(
                    main(["--root", tmp, "--titan", titan, "--go"]), 0
                )
            self.assertIn("No allocation and no write", reread_out.getvalue())
            self.assertIn('"state": "NOT_LANDED"', reread_out.getvalue())
            with open(titan, "rb") as handle:
                self.assertEqual(handle.read(), written_once)

    def test_applying_packet_resumes_original_offsets(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet_dir = os.path.join(tmp, "excerpts", "20260823")
            os.makedirs(packet_dir)
            titan = os.path.join(tmp, "titan.gguf")
            one, two = b"organ one", b"organ two"
            with open(os.path.join(packet_dir, "one.mno"), "wb") as handle:
                handle.write(one)
            with open(os.path.join(packet_dir, "two.mno"), "wb") as handle:
                handle.write(two)
            with open(titan, "wb") as handle:
                handle.write(b"GGUF" + one)  # crash after the first append
            packet = {
                "kind": "TITAN_MOVE_PACKET",
                "state": "APPLYING",
                "titan": "NOT_WRITTEN",
                "count": 2,
                "claimed_append_base": 4,
                "claimed_append_end": 4 + len(one) + len(two),
                "titan_size_before": 4,
                "organs": [
                    {
                        "name": "one",
                        "container": "one.mno",
                        "offset": 4,
                        "len": len(one),
                        "sha256": hashlib.sha256(one).hexdigest(),
                        "pre_len": 0,
                        "pre_sha256": hashlib.sha256(b"").hexdigest(),
                    },
                    {
                        "name": "two",
                        "container": "two.mno",
                        "offset": 4 + len(one),
                        "len": len(two),
                        "sha256": hashlib.sha256(two).hexdigest(),
                        "pre_len": 0,
                        "pre_sha256": hashlib.sha256(b"").hexdigest(),
                    },
                ],
            }
            packet_path = os.path.join(packet_dir, "titan_move_packet.json")
            with open(packet_path, "w") as handle:
                json.dump(packet, handle)
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--root", tmp, "--titan", titan, "--go"])
            self.assertEqual(code, 0, out.getvalue())
            with open(titan, "rb") as handle:
                self.assertEqual(handle.read(), b"GGUF" + one + two)
            with open(packet_path) as handle:
                landed = json.load(handle)
            self.assertEqual(landed["claimed_append_base"], 4)
            self.assertEqual(
                landed["claimed_append_end"], 4 + len(one) + len(two)
            )
            self.assertEqual(landed["past_eof_count"], 2)
            self.assertTrue(all(row["pre_len"] == 0 for row in landed["organs"]))
            self.assertTrue(all(
                row["pre_sha256"] == hashlib.sha256(b"").hexdigest()
                for row in landed["organs"]
            ))

    def test_applying_uses_exact_persisted_offsets(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet_dir = os.path.join(tmp, "excerpts", "20260823")
            os.makedirs(packet_dir)
            titan = os.path.join(tmp, "titan.gguf")
            one, two = b"one", b"two"
            for name, body in (("one", one), ("two", two)):
                with open(os.path.join(packet_dir, name + ".mno"), "wb") as handle:
                    handle.write(body)
            with open(titan, "wb") as handle:
                handle.write(b"GGUF" + one)
            empty_sha = hashlib.sha256(b"").hexdigest()
            packet = {
                "kind": "TITAN_MOVE_PACKET",
                "state": "APPLYING",
                "titan": "NOT_WRITTEN",
                "count": 2,
                "claimed_append_base": 4,
                "claimed_append_end": 11,
                "titan_size_before": 4,
                "organs": [
                    {
                        "name": "one",
                        "container": "one.mno",
                        "offset": 4,
                        "len": len(one),
                        "sha256": hashlib.sha256(one).hexdigest(),
                        "pre_len": 0,
                        "pre_sha256": empty_sha,
                    },
                    {
                        "name": "two",
                        "container": "two.mno",
                        "offset": 8,
                        "len": len(two),
                        "sha256": hashlib.sha256(two).hexdigest(),
                        "pre_len": 0,
                        "pre_sha256": empty_sha,
                    },
                ],
            }
            packet_path = os.path.join(packet_dir, "titan_move_packet.json")
            with open(packet_path, "w") as handle:
                json.dump(packet, handle)
            with open(packet_path, "rb") as handle:
                packet_before = handle.read()
            with open(titan, "rb") as handle:
                titan_before = handle.read()
            with self.assertRaisesRegex(RuntimeError, "non-contiguous MOVE geometry"):
                main(["--root", tmp, "--titan", titan, "--go"])
            with open(packet_path, "rb") as handle:
                self.assertEqual(handle.read(), packet_before)
            with open(titan, "rb") as handle:
                self.assertEqual(handle.read(), titan_before)

    def test_active_incident_blocks_all_move_mutation_states(self):
        for state in ("NOT_WRITTEN", "APPLYING"):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as tmp:
                packet_dir = os.path.join(tmp, "excerpts", "20260823")
                os.makedirs(packet_dir)
                organ = b"x"
                with open(os.path.join(packet_dir, "one.mno"), "wb") as handle:
                    handle.write(organ)
                titan = os.path.join(tmp, "titan.gguf")
                with open(titan, "wb") as handle:
                    handle.write(b"GGUF")
                row = {
                    "name": "one",
                    "container": "one.mno",
                    "offset": 4,
                    "len": 1,
                    "sha256": hashlib.sha256(organ).hexdigest(),
                }
                if state == "APPLYING":
                    row["pre_len"] = 0
                    row["pre_sha256"] = hashlib.sha256(b"").hexdigest()
                packet = {
                    "kind": "TITAN_MOVE_PACKET",
                    "state": state,
                    "titan": "NOT_WRITTEN",
                    "count": 1,
                    "claimed_append_base": 4,
                    "claimed_append_end": 5,
                    "titan_size_before": 4,
                    "duplicate_append_incident": {
                        "state": "PAUSED_DUPLICATE_APPENDS"
                    },
                    "organs": [row],
                }
                packet_path = os.path.join(packet_dir, "titan_move_packet.json")
                with open(packet_path, "w") as handle:
                    json.dump(packet, handle)
                with open(packet_path, "rb") as handle:
                    packet_before = handle.read()
                with open(titan, "rb") as handle:
                    titan_before = handle.read()
                out = io.StringIO()
                with redirect_stdout(out):
                    code = main(["--root", tmp, "--titan", titan, "--go"])
                self.assertEqual(code, 2, out.getvalue())
                self.assertIn("PAUSED all Titan MOVE mutation", out.getvalue())
                with open(packet_path, "rb") as handle:
                    self.assertEqual(handle.read(), packet_before)
                with open(titan, "rb") as handle:
                    self.assertEqual(handle.read(), titan_before)

    def test_preflight_failure_leaves_titan_and_packet_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet_dir = os.path.join(tmp, "excerpts", "20260823")
            os.makedirs(packet_dir)
            titan = os.path.join(tmp, "titan.gguf")
            one, two = b"organ one", b"organ two"
            with open(titan, "wb") as handle:
                handle.write(b"GGUF")
            with open(os.path.join(packet_dir, "one.mno"), "wb") as handle:
                handle.write(one)
            with open(os.path.join(packet_dir, "two.mno"), "wb") as handle:
                handle.write(two)
            packet = {
                "kind": "TITAN_MOVE_PACKET",
                "titan": "NOT_WRITTEN",
                "count": 2,
                "claimed_append_base": 4,
                "claimed_append_end": 4 + len(one) + len(two),
                "organs": [
                    {
                        "name": "one",
                        "container": "one.mno",
                        "offset": 4,
                        "len": len(one),
                        "sha256": hashlib.sha256(one).hexdigest(),
                    },
                    {
                        "name": "two",
                        "container": "two.mno",
                        "offset": 4 + len(one),
                        "len": len(two),
                        "sha256": hashlib.sha256(b"wrong").hexdigest(),
                    },
                ],
            }
            packet_path = os.path.join(packet_dir, "titan_move_packet.json")
            with open(packet_path, "w") as handle:
                json.dump(packet, handle)
            with open(packet_path, "rb") as handle:
                packet_before = handle.read()
            with open(titan, "rb") as handle:
                titan_before = handle.read()
            with self.assertRaisesRegex(RuntimeError, "len/sha mismatch"):
                main(["--root", tmp, "--titan", titan, "--go"])
            with open(packet_path, "rb") as handle:
                packet_after = handle.read()
            with open(titan, "rb") as handle:
                titan_after = handle.read()
            self.assertEqual(packet_after, packet_before)
            self.assertEqual(titan_after, titan_before)

    def test_preflight_refuses_container_identity_changes_without_writes(self):
        invalid_packets = (
            (
                "duplicated/substituted",
                [
                    {"name": "one", "container": "one.mno"},
                    {"name": "two", "container": "one.mno"},
                ],
            ),
            (
                "substituted",
                [{"name": "one", "container": "two.mno"}],
            ),
            (
                "non-basename",
                [{"name": "one", "container": "nested/one.mno"}],
            ),
        )
        for label, identities in invalid_packets:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                packet_dir = os.path.join(tmp, "excerpts", "20260823")
                os.makedirs(packet_dir)
                organ = b"same source bytes"
                for container in ("one.mno", "two.mno"):
                    with open(os.path.join(packet_dir, container), "wb") as handle:
                        handle.write(organ)
                organs = []
                offset = 4
                for identity in identities:
                    row = dict(identity)
                    row.update({
                        "offset": offset,
                        "len": len(organ),
                        "sha256": hashlib.sha256(organ).hexdigest(),
                    })
                    organs.append(row)
                    offset += len(organ)
                packet = {
                    "kind": "TITAN_MOVE_PACKET",
                    "titan": "NOT_WRITTEN",
                    "count": len(organs),
                    "claimed_append_base": 4,
                    "claimed_append_end": offset,
                    "organs": organs,
                }
                packet_path = os.path.join(
                    packet_dir, "titan_move_packet.json"
                )
                with open(packet_path, "w") as handle:
                    json.dump(packet, handle)
                target = os.path.join(tmp, "arbitrary-target.bin")
                with open(target, "wb") as handle:
                    handle.write(b"GGUF")
                with open(packet_path, "rb") as handle:
                    packet_before = handle.read()
                with open(target, "rb") as handle:
                    target_before = handle.read()
                with self.assertRaisesRegex(RuntimeError, "source container"):
                    main(["--root", tmp, "--titan", target, "--go"])
                with open(packet_path, "rb") as handle:
                    self.assertEqual(handle.read(), packet_before)
                with open(target, "rb") as handle:
                    self.assertEqual(handle.read(), target_before)

    def test_go_rejects_non_gguf_content_without_path_allowlist(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet_dir = os.path.join(tmp, "excerpts", "20260823")
            os.makedirs(packet_dir)
            organ = b"organ"
            with open(os.path.join(packet_dir, "one.mno"), "wb") as handle:
                handle.write(organ)
            packet = {
                "kind": "TITAN_MOVE_PACKET",
                "titan": "NOT_WRITTEN",
                "count": 1,
                "claimed_append_base": 10,
                "organs": [{
                    "name": "one",
                    "container": "one.mno",
                    "len": len(organ),
                    "sha256": hashlib.sha256(organ).hexdigest(),
                }],
            }
            with open(os.path.join(packet_dir, "titan_move_packet.json"), "w") as handle:
                json.dump(packet, handle)
            wrong = os.path.join(tmp, "unrelated.bin")
            with open(wrong, "wb") as handle:
                handle.write(b"NOT A GGUF")
            with open(wrong, "rb") as handle:
                before = handle.read()
            with self.assertRaisesRegex(RuntimeError, "not a measured GGUF"):
                main(["--root", tmp, "--titan", wrong, "--go"])
            with open(wrong, "rb") as handle:
                self.assertEqual(handle.read(), before)

    def test_go_accepts_explicit_gguf_under_arbitrary_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet_dir = os.path.join(tmp, "excerpts", "20260823")
            os.makedirs(packet_dir)
            organ = b"organ"
            with open(os.path.join(packet_dir, "one.mno"), "wb") as handle:
                handle.write(organ)
            packet = {
                "kind": "TITAN_MOVE_PACKET",
                "titan": "NOT_WRITTEN",
                "count": 1,
                "claimed_append_base": 4,
                "organs": [{
                    "name": "one",
                    "container": "one.mno",
                    "len": len(organ),
                    "sha256": hashlib.sha256(organ).hexdigest(),
                }],
            }
            packet_path = os.path.join(packet_dir, "titan_move_packet.json")
            with open(packet_path, "w") as handle:
                json.dump(packet, handle)
            target = os.path.join(tmp, "open-target.bin")
            with open(target, "wb") as handle:
                handle.write(b"GGUF")
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(
                    main(["--root", tmp, "--titan", target, "--go"]), 0
                )
            with open(target, "rb") as handle:
                self.assertEqual(handle.read(), b"GGUF" + organ)

    def test_applying_refuses_truncated_target_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet_dir = os.path.join(tmp, "excerpts", "20260823")
            os.makedirs(packet_dir)
            organ = b"organ"
            with open(os.path.join(packet_dir, "one.mno"), "wb") as handle:
                handle.write(organ)
            titan = os.path.join(tmp, "titan.gguf")
            with open(titan, "wb") as handle:
                handle.write(b"GGUF")
            packet = {
                "kind": "TITAN_MOVE_PACKET",
                "state": "APPLYING",
                "titan": "NOT_WRITTEN",
                "count": 1,
                "claimed_append_base": 8,
                "claimed_append_end": 8 + len(organ),
                "titan_size_before": 8,
                "organs": [{
                    "name": "one",
                    "container": "one.mno",
                    "offset": 8,
                    "len": len(organ),
                    "sha256": hashlib.sha256(organ).hexdigest(),
                    "pre_len": 0,
                    "pre_sha256": hashlib.sha256(b"").hexdigest(),
                }],
            }
            packet_path = os.path.join(packet_dir, "titan_move_packet.json")
            with open(packet_path, "w") as handle:
                json.dump(packet, handle)
            with open(titan, "rb") as handle:
                before = handle.read()
            with self.assertRaisesRegex(RuntimeError, "outside fixed append span"):
                main(["--root", tmp, "--titan", titan, "--go"])
            with open(titan, "rb") as handle:
                self.assertEqual(handle.read(), before)

    def test_applying_refuses_false_original_preimage(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet_dir = os.path.join(tmp, "excerpts", "20260823")
            os.makedirs(packet_dir)
            organ = b"organ"
            with open(os.path.join(packet_dir, "one.mno"), "wb") as handle:
                handle.write(organ)
            titan = os.path.join(tmp, "titan.gguf")
            with open(titan, "wb") as handle:
                handle.write(b"GGUF")
            packet = {
                "kind": "TITAN_MOVE_PACKET",
                "state": "APPLYING",
                "titan": "NOT_WRITTEN",
                "count": 1,
                "claimed_append_base": 4,
                "claimed_append_end": 4 + len(organ),
                "titan_size_before": 4,
                "organs": [{
                    "name": "one",
                    "container": "one.mno",
                    "offset": 4,
                    "len": len(organ),
                    "sha256": hashlib.sha256(organ).hexdigest(),
                    "pre_len": 1,
                    "pre_sha256": hashlib.sha256(b"x").hexdigest(),
                }],
            }
            packet_path = os.path.join(packet_dir, "titan_move_packet.json")
            with open(packet_path, "w") as handle:
                json.dump(packet, handle)
            with open(titan, "rb") as handle:
                before = handle.read()
            with self.assertRaisesRegex(RuntimeError, "original preimage"):
                main(["--root", tmp, "--titan", titan, "--go"])
            with open(titan, "rb") as handle:
                self.assertEqual(handle.read(), before)

    def test_applying_refuses_occupied_nonprefix_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet_dir = os.path.join(tmp, "excerpts", "20260823")
            os.makedirs(packet_dir)
            organ = b"\x01"
            with open(os.path.join(packet_dir, "one.mno"), "wb") as handle:
                handle.write(organ)
            titan = os.path.join(tmp, "titan.gguf")
            with open(titan, "wb") as handle:
                handle.write(b"GGUF\x80")
            packet = {
                "kind": "TITAN_MOVE_PACKET",
                "state": "APPLYING",
                "titan": "NOT_WRITTEN",
                "count": 1,
                "claimed_append_base": 4,
                "claimed_append_end": 5,
                "titan_size_before": 4,
                "organs": [{
                    "name": "one",
                    "container": "one.mno",
                    "offset": 4,
                    "len": 1,
                    "sha256": hashlib.sha256(organ).hexdigest(),
                    "pre_len": 0,
                    "pre_sha256": hashlib.sha256(b"").hexdigest(),
                }],
            }
            packet_path = os.path.join(packet_dir, "titan_move_packet.json")
            with open(packet_path, "w") as handle:
                json.dump(packet, handle)
            with open(titan, "rb") as handle:
                before = handle.read()
            with self.assertRaisesRegex(RuntimeError, "not the exact written prefix"):
                main(["--root", tmp, "--titan", titan, "--go"])
            with open(titan, "rb") as handle:
                self.assertEqual(handle.read(), before)


if __name__ == "__main__":
    unittest.main()
