#!/usr/bin/env python3
"""Titan MOVE dry measure is a measurement, not a titan write."""

from __future__ import annotations

import copy
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from titan_move_dry import (
    classify,
    measure_from_packet,
    measure_tree,
)


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
        self.assertIn("inconsistent", verdict["note"])
        self.assertIn("31/31", verdict["note"])

    def test_journal_reread_without_titan_is_candidate(self):
        measured = {
            "measured": True,
            "count": 31,
            "excerpt_count": 31,
            "titan": "NOT_WRITTEN",
            "nonzero_offsets": 31,
            "reread": False,
            "journal_reread": True,
            "journal_count": 31,
            "plan_structure_complete": True,
        }
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "CANDIDATE")
        self.assertIn("journaled", verdict["note"])

    def test_claimed_offsets_without_write_are_claimed(self):
        measured = {
            "measured": True,
            "count": 31,
            "excerpt_count": 31,
            "titan": "NOT_WRITTEN",
            "nonzero_offsets": 31,
            "reread": False,
            "plan_structure_complete": True,
        }
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "CLAIMED")
        self.assertIn("claimed append", verdict["note"])
        self.assertIn("do not append", verdict["note"])

    def test_written_and_reread_is_integrated(self):
        measured = {
            "measured": True,
            "count": 31,
            "excerpt_count": 31,
            "sha_ok": 31,
            "titan": "WRITTEN",
            "nonzero_offsets": 31,
            "packet_state": "INTEGRATED",
            "wrote": True,
            "reread": True,
            "write_count": 31,
            "reread_count": 31,
            "past_eof_count": 31,
            "claimed_append_base": 100,
            "claimed_append_end": 200,
            "titan_size_before": 100,
            "titan_size_after": 200,
            "written_bytes": 100,
            "write_receipt": "p/owner-write.md",
            "structure_complete": True,
            "write_receipt_exists": True,
            "write_receipt_content_ok": True,
            "integrated_commit_ok": True,
            "legacy_aliases_ok": True,
            "independent_measurement_ok": True,
        }
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("31", verdict["note"])

    def test_duplicate_append_incident_overrides_historical_closure(self):
        measured = {
            "measured": True,
            "incident_active": True,
            "incident_evidence_ok": True,
            "span_count": 3,
            "span_bytes": 9319291,
            "observed_titan_size": 103831308164,
            "duplicate_span_count": 2,
        }
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("PAUSED", verdict["note"])
        self.assertIn("2 duplicate", verdict["note"])
        measured["incident_evidence_ok"] = False
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("FINDER-FAILED", verdict["note"])

    def test_written_marker_without_reread_evidence_is_not_landed(self):
        measured = {
            "measured": True,
            "count": 31,
            "excerpt_count": 31,
            "sha_ok": 31,
            "titan": "WRITTEN",
            "nonzero_offsets": 31,
            "reread": False,
        }
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("marker-only", verdict["note"])

    def test_integrated_packet_rejects_bad_geometry_length_and_commit(self):
        packet_path = os.path.join(
            ROOT, "excerpts", "20260823", "titan_move_packet.json"
        )
        excerpt_dir = os.path.dirname(packet_path)
        with open(packet_path, encoding="utf-8") as handle:
            original = json.load(handle)
        mutations = []
        duplicate = copy.deepcopy(original)
        duplicate["organs"][1]["offset"] = duplicate["organs"][0]["offset"]
        mutations.append(duplicate)
        wrong_len = copy.deepcopy(original)
        wrong_len["organs"][0]["len"] += 1
        mutations.append(wrong_len)
        bad_end = copy.deepcopy(original)
        bad_end["claimed_append_end"] += 1
        mutations.append(bad_end)
        bad_commit = copy.deepcopy(original)
        bad_commit["integrated_commit"] = ""
        mutations.append(bad_commit)
        fake_receipt = copy.deepcopy(original)
        fake_receipt["write_receipt"] = "p/fake.md"
        mutations.append(fake_receipt)
        bad_alias = copy.deepcopy(original)
        bad_alias["live_size_after"] -= 1
        mutations.append(bad_alias)
        for packet in mutations:
            row = measure_from_packet(packet, excerpt_dir)
            self.assertEqual(classify(row)["state"], "NOT_LANDED")

    def test_integrated_packet_rejects_duplicate_container_omission(self):
        packet_path = os.path.join(
            ROOT, "excerpts", "20260823", "titan_move_packet.json"
        )
        excerpt_dir = os.path.dirname(packet_path)
        with open(packet_path, encoding="utf-8") as handle:
            packet = json.load(handle)
        source = next(row for row in packet["organs"] if row["len"] == 570)
        omitted = next(
            row
            for row in packet["organs"]
            if row["len"] == 570 and row["name"] != source["name"]
        )
        omitted["container"] = source["container"]
        omitted["path"] = source["path"]
        omitted["sha256"] = source["sha256"]
        row = measure_from_packet(packet, excerpt_dir)
        self.assertEqual(row["excerpt_count"], 31)
        self.assertEqual(row["sha_ok"], 31)
        self.assertEqual(row["unique_container_count"], 30)
        self.assertFalse(row["canonical_membership_complete"])
        self.assertFalse(row["structure_complete"])
        self.assertEqual(classify(row)["state"], "NOT_LANDED")

    def test_not_written_plan_requires_unique_contiguous_hash_truth(self):
        packet_path = os.path.join(
            ROOT, "excerpts", "20260823", "titan_move_packet.json"
        )
        excerpt_dir = os.path.dirname(packet_path)
        with open(packet_path, encoding="utf-8") as handle:
            packet = json.load(handle)
        packet["titan"] = "NOT_WRITTEN"
        packet.pop("state", None)
        for row in packet["organs"]:
            row["titan"] = "NOT_WRITTEN"
        packet["organs"][1]["offset"] = packet["organs"][0]["offset"]
        row = measure_from_packet(packet, excerpt_dir)
        row["journal_reread"] = True
        row["journal_count"] = 31
        self.assertFalse(row["plan_structure_complete"])
        self.assertEqual(classify(row)["state"], "NOT_LANDED")

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

    def test_live_tree_is_thirty_one_and_incident_paused(self):
        row = measure_tree(ROOT)
        self.assertTrue(row["measured"], row)
        self.assertGreaterEqual(row["excerpt_count"], 31)
        self.assertEqual(row["titan"], "WRITTEN")
        self.assertEqual(row["nonzero_offsets"], 31)
        self.assertEqual(row["sha_ok"], 31)
        self.assertEqual(row["len_ok"], 31)
        self.assertEqual(row["canonical_container_count"], 31)
        self.assertEqual(row["unique_container_count"], 31)
        self.assertEqual(row["unique_path_count"], 31)
        self.assertTrue(row["canonical_membership_complete"])
        self.assertTrue(row["structure_complete"])
        self.assertTrue(row["write_receipt_exists"])
        self.assertTrue(row["write_receipt_content_ok"])
        self.assertTrue(row["integrated_commit_ok"])
        self.assertTrue(row["legacy_aliases_ok"])
        self.assertEqual(row["write_count"], 31)
        self.assertEqual(row["live_size_before"], row["titan_size_before"])
        self.assertEqual(row["live_size_after"], row["titan_size_after"])
        self.assertTrue(row["reread"])
        self.assertEqual(row["reread_count"], 31)
        self.assertEqual(row["past_eof_count"], 31)
        self.assertTrue(row["incident_active"])
        self.assertTrue(row["incident_evidence_ok"])
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(row["payload_bytes"], 9319291)
        self.assertEqual(
            row["payload_sha256"],
            "3754028086cd42e00131bea88f0e7fcf6dba2f84ad31cb70b88e655bbdd84e8c",
        )
        self.assertEqual(row["observed_titan_size"], 103831308164)
        self.assertEqual(row["span_count"], 3)
        self.assertEqual(row["duplicate_span_count"], 2)
        verdict = classify(row)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("PAUSED", verdict["note"])


if __name__ == "__main__":
    unittest.main()
