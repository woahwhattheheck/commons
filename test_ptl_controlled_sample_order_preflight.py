#!/usr/bin/env python3
"""Acceptance tests for ptl-controlled-sample-order-preflight-01."""

from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import ptl_controlled_sample_order_preflight as gate


class PtlControlledSampleOrderPreflightTests(unittest.TestCase):
    def test_locked_fixture_is_twelve_synthetic_redacted_packets(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 12)
        self.assertEqual(len({row["packet_id"] for row in rows}), 12)
        self.assertTrue(all(row["synthetic"] and row["redacted"] for row in rows))

    def test_exact_seven_ready_five_hold_and_one_each_reason(self) -> None:
        result = gate.run_preflight()
        self.assertEqual(gate.pass_contract(result), [])
        self.assertEqual(result["audit"]["ready_count"], 7)
        self.assertEqual(result["audit"]["hold_count"], 5)
        self.assertEqual(
            result["audit"]["hold_code_counts"],
            {code: 1 for code in gate.ACCEPTANCE_HOLD_CODES},
        )

    def test_both_runs_are_byte_identical_with_same_audit_hash(self) -> None:
        first = gate.run_preflight()
        second = gate.run_preflight()
        self.assertEqual(gate.canonical_output(first), gate.canonical_output(second))
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(len(first["audit_sha256"]), 64)
        self.assertEqual(first["audit_sha256"], gate.sha256_hex(first["audit"]))
        self.assertEqual(
            first["audit_sha256"],
            "22f96bb85310f59fd615a1e528961c1bd5ca919850f230d5a923ec21b6020257",
        )
        self.assertEqual(
            hashlib.sha256(gate.canonical_output(first)).hexdigest(),
            "01bb6796c156c199560e48c67a4755411297fbb67c670b4fdd2b2996322d829a",
        )

    def test_ready_packets_carry_every_required_preflight_fact(self) -> None:
        by_id = {row["packet_id"]: row for row in gate.build_acceptance_fixture()}
        result = gate.run_preflight()
        ready = [item for item in result["decisions"] if item["state"] == gate.READY]
        self.assertEqual(len(ready), 7)
        for decision in ready:
            source = by_id[decision["packet_id"]]
            self.assertTrue(source["lso_present"])
            self.assertTrue(source["order_id"])
            self.assertTrue(source["po_number"] or source["payment_status"] == "APPROVED")
            self.assertTrue(not source["sds_required"] or source["sds_present"])
            self.assertTrue(not source["dea_222_required"] or source["dea_222_present"])
            if source["international"]:
                self.assertTrue(all(source[field] for field in gate.INTERNATIONAL_FIELDS))
            self.assertTrue(source["requested_turnaround"])
            self.assertTrue(source["report_delivery_route"])
            self.assertTrue(decision["named_human_accession_required"])

    def test_malformed_or_omitted_condition_inputs_fail_closed(self) -> None:
        base = gate.build_acceptance_fixture()[0]
        bad_values = [None, [], "packet"]
        for value in bad_values:
            decision = gate.classify_packet(value)
            self.assertEqual(decision["state"], gate.HOLD)
            self.assertEqual(decision["reason_code"], "MALFORMED_PACKET")
        for field in (
            "sds_required",
            "sds_present",
            "dea_222_required",
            "dea_222_present",
            "international",
        ):
            packet = deepcopy(base)
            packet.pop(field)
            decision = gate.classify_packet(packet)
            self.assertEqual(decision["state"], gate.HOLD)
            self.assertEqual(decision["reason_code"], "MALFORMED_PACKET")

    def test_exact_hold_fixture_rows_have_the_locked_codes(self) -> None:
        result = gate.run_preflight()
        holds = [item for item in result["decisions"] if item["state"] == gate.HOLD]
        self.assertEqual(
            [item["reason_code"] for item in holds],
            list(gate.ACCEPTANCE_HOLD_CODES),
        )

    def test_decisions_never_create_accession_release_payment_or_transport(self) -> None:
        result = gate.run_preflight()
        audit = result["audit"]
        self.assertEqual(audit["real_customer_records"], 0)
        self.assertEqual(audit["accessions_created"], 0)
        self.assertEqual(audit["releases_created"], 0)
        self.assertEqual(audit["payment_actions"], 0)
        self.assertEqual(audit["external_transmissions"], 0)
        self.assertFalse(audit["autonomous_action"])
        self.assertTrue(all(item["state"] in {gate.READY, gate.HOLD} for item in result["decisions"]))

    def test_json_input_loader_accepts_list_or_packets_envelope(self) -> None:
        rows = gate.build_acceptance_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            direct = Path(tmp) / "direct.json"
            wrapped = Path(tmp) / "wrapped.json"
            direct.write_text(json.dumps(rows), encoding="utf-8")
            wrapped.write_text(json.dumps({"packets": rows}), encoding="utf-8")
            self.assertEqual(gate.load_packets(str(direct)), rows)
            self.assertEqual(gate.load_packets(str(wrapped)), rows)


if __name__ == "__main__":
    unittest.main()
