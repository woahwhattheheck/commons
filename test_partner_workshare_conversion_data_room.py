from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from revenue.partner_workshare_conversion_data_room.engine import (
    AUTHORITY_CEILING,
    COMMERCIAL_STATE,
    PacketError,
    compile_packet,
    load_strict_json,
    verify_bundle,
)

ROOT = Path(__file__).resolve().parent
EXAMPLE = ROOT / "revenue" / "partner_workshare_conversion_data_room" / "example.json"


def candidate():
    return load_strict_json(EXAMPLE.read_text(encoding="utf-8"))


class WorkshareDataRoomTest(unittest.TestCase):
    def test_ready_example_is_internal_only(self):
        result = compile_packet(candidate())
        self.assertEqual(result.decision, "READY_FOR_OWNER_REVIEW")
        self.assertEqual(result.blockers, ())
        packet = json.loads(result.packet_json)
        self.assertEqual(packet["derived"]["commercial_state"], COMMERCIAL_STATE)
        self.assertEqual(packet["derived"]["authority_ceiling"], AUTHORITY_CEILING)
        self.assertTrue(all(value is False for value in AUTHORITY_CEILING.values()))
        self.assertIn("Internal owner-review packet only", result.packet_markdown)
        self.assertTrue(verify_bundle(candidate(), result.packet_json, result.packet_markdown, result.receipt_json))

    def test_proposed_risk_claim_holds(self):
        data = candidate()
        data["claims"][0]["kind"] = "QUALIFICATION"
        data["claims"][0]["state"] = "PROPOSED"
        result = compile_packet(data)
        self.assertEqual(result.decision, "HOLD")
        self.assertTrue(any("claim claim-cap" in item for item in result.blockers))
        self.assertTrue(any("capability slice-reconcile" in item for item in result.blockers))

    def test_risky_claim_secondary_evidence_holds(self):
        data = candidate()
        data["claims"][0]["kind"] = "CERTIFICATION"
        data["evidence"][2]["authority"] = "SECONDARY"
        result = compile_packet(data)
        self.assertEqual(result.decision, "HOLD")
        self.assertIn("claim claim-cap: risk-bearing claim lacks primary retained authority", result.blockers)

    def test_pricing_without_owner_authority_holds(self):
        data = candidate()
        price = next(item for item in data["evidence"] if item["id"] == "ev-price")
        price["kind"] = "CAPABILITY_PROOF"
        result = compile_packet(data)
        self.assertEqual(result.decision, "HOLD")
        self.assertIn("proposed pricing lacks current OWNER_PRICING_AUTHORITY evidence", result.blockers)

    def test_placeholder_pricing_cannot_smuggle_amount(self):
        data = candidate()
        data["pricing_basis"]["status"] = "PLACEHOLDER"
        with self.assertRaisesRegex(PacketError, "PLACEHOLDER"):
            compile_packet(data)

    def test_security_owner_input_holds(self):
        data = candidate()
        data["security_access"][0]["state"] = "OWNER_INPUT"
        result = compile_packet(data)
        self.assertEqual(result.decision, "HOLD")
        self.assertIn("security/access access-readonly is OWNER_INPUT", result.blockers)

    def test_expired_and_future_evidence_hold(self):
        data = candidate()
        price = next(item for item in data["evidence"] if item["id"] == "ev-price")
        price["expires_at_utc"] = "2026-09-17T17:00:00Z"
        cap = next(item for item in data["evidence"] if item["id"] == "ev-cap")
        cap["observed_at_utc"] = "2026-09-17T19:00:00Z"
        result = compile_packet(data)
        self.assertEqual(result.decision, "HOLD")
        self.assertTrue(any("ev-price is expired" in item for item in result.blockers))
        self.assertTrue(any("ev-cap is future-dated" in item for item in result.blockers))

    def test_deadline_closes_ready_state(self):
        data = candidate()
        data["evaluation_at_utc"] = data["opportunity"]["deadline_utc"]
        result = compile_packet(data)
        self.assertEqual(result.decision, "HOLD")
        self.assertIn("opportunity deadline is closed at retained evaluation time", result.blockers)

    def test_workshare_owner_conflict_rejected(self):
        data = candidate()
        data["workshare"][0]["owner_party_id"] = "primeco"
        with self.assertRaisesRegex(PacketError, "owner conflicts"):
            compile_packet(data)

    def test_duplicate_workshare_assignment_rejected(self):
        data = candidate()
        dup = copy.deepcopy(data["workshare"][0])
        dup["id"] = "ws-reconcile-2"
        data["workshare"].append(dup)
        with self.assertRaisesRegex(PacketError, "multiple workshare assignments"):
            compile_packet(data)

    def test_dangling_ref_rejected(self):
        data = candidate()
        data["claims"][0]["evidence_refs"] = ["missing"]
        with self.assertRaisesRegex(PacketError, "unknown ids"):
            compile_packet(data)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(PacketError, "duplicate JSON key"):
            load_strict_json('{"a":1,"a":2}')

    def test_nonfinite_rejected(self):
        with self.assertRaisesRegex(PacketError, "non-finite"):
            load_strict_json('{"a":NaN}')

    def test_bool_as_amount_rejected(self):
        data = candidate()
        data["pricing_basis"]["amount_minor"] = True
        with self.assertRaisesRegex(PacketError, "bool is rejected"):
            compile_packet(data)

    def test_unknown_fields_rejected(self):
        data = candidate()
        data["magic"] = "unsafe"
        with self.assertRaisesRegex(PacketError, "unknown fields"):
            compile_packet(data)

    def test_unsafe_or_credential_url_rejected(self):
        data = candidate()
        data["evidence"][0]["source_uri"] = "https://user:pass@example.gov/x"
        with self.assertRaisesRegex(PacketError, "without userinfo"):
            compile_packet(data)

    def test_input_order_is_canonical(self):
        a = candidate()
        b = copy.deepcopy(a)
        for key in ("parties", "evidence", "claims", "capability_slices", "workshare", "exclusions", "assumptions", "security_access", "acceptance_questions"):
            b[key] = list(reversed(b[key]))
        ra = compile_packet(a)
        rb = compile_packet(b)
        self.assertEqual(ra.packet_json, rb.packet_json)
        self.assertEqual(ra.packet_markdown, rb.packet_markdown)
        self.assertEqual(ra.receipt_json, rb.receipt_json)

    def test_tamper_detected_even_when_one_receipt_digest_is_resealed(self):
        data = candidate()
        result = compile_packet(data)
        packet = json.loads(result.packet_json)
        packet["derived"]["truth_note"] = "accepted"
        tampered = json.dumps(packet, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        receipt = json.loads(result.receipt_json)
        import hashlib
        receipt["packet_json_sha256"] = hashlib.sha256(tampered.encode()).hexdigest()
        resealed = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        with self.assertRaisesRegex(PacketError, "semantic recompile"):
            verify_bundle(data, tampered, result.packet_markdown, resealed)

    def test_cli_compile_verify_and_overwrite_refusal(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "input.json"
            src.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
            prefix = Path(td) / "room"
            cmd = [sys.executable, "-m", "revenue.partner_workshare_conversion_data_room.cli"]
            first = subprocess.run(cmd + ["compile", str(src), str(prefix)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("READY_FOR_OWNER_REVIEW", first.stdout)
            verify = subprocess.run(
                cmd + ["verify", str(src), str(prefix.with_suffix('.packet.json')), str(prefix.with_suffix('.packet.md')), str(prefix.with_suffix('.receipt.json'))],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(verify.returncode, 0, verify.stderr)
            self.assertIn("VALID", verify.stdout)
            second = subprocess.run(cmd + ["compile", str(src), str(prefix)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(second.returncode, 2)
            self.assertIn("File exists", second.stderr)


if __name__ == "__main__":
    unittest.main()
