#!/usr/bin/env python3
"""Hostile tests for tools.procurement_win_loss."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from tools.procurement_win_loss.compiler import OutcomeError, compile_record, loads_strict
from tools.procurement_win_loss.verifier import VerificationError, verify_record


ROOT = Path(__file__).resolve().parent
FIXTURES = json.loads((ROOT / "tools" / "procurement_win_loss" / "fixtures.json").read_text(encoding="utf-8"))


class ProcurementWinLossTests(unittest.TestCase):
    def test_all_valid_fixtures_compile_and_verify(self):
        for row in FIXTURES["valid"]:
            with self.subTest(row=row["name"]):
                receipt = compile_record(row["record"])
                self.assertEqual(receipt["outcome"], row["expected_outcome"])
                verified = verify_record(row["record"], receipt)
                self.assertEqual(verified["status"], "VERIFIED")
                self.assertEqual(verified["outcome"], row["expected_outcome"])

    def test_invalid_fixtures_fail_closed(self):
        for row in FIXTURES["invalid"]:
            with self.subTest(row=row["name"]):
                with self.assertRaisesRegex(OutcomeError, row["error_contains"]):
                    compile_record(row["record"])

    def test_not_selected_without_reason_does_not_invent_cause(self):
        row = next(item for item in FIXTURES["valid"] if item["name"] == "lost_reason_unknown")
        receipt = compile_record(row["record"])
        self.assertEqual(receipt["outcome"], "LOST")
        self.assertEqual(receipt["rationale"]["status"], "UNKNOWN")
        self.assertEqual(receipt["rationale"]["statements"], [])
        self.assertEqual(receipt["unknowns"], ["rationale"])
        self.assertFalse(receipt["authority"]["causal_inference_authorized"])

    def test_evidence_order_is_canonical(self):
        row = next(item for item in FIXTURES["valid"] if item["name"] == "chronology_pending_then_terminal")
        a = copy.deepcopy(row["record"])
        b = copy.deepcopy(row["record"])
        b["evidence"].reverse()
        self.assertEqual(compile_record(a), compile_record(b))

    def test_current_conflict_has_named_hold(self):
        row = next(item for item in FIXTURES["valid"] if item["name"] == "conflicting_current_terminal_evidence")
        receipt = compile_record(row["record"])
        self.assertEqual(receipt["outcome"], "UNKNOWN")
        self.assertIn("conflicting_current_terminal_evidence", receipt["hold_reasons"])

    def test_stale_terminal_does_not_become_win(self):
        row = next(item for item in FIXTURES["valid"] if item["name"] == "stale_terminal_cannot_decide")
        receipt = compile_record(row["record"])
        self.assertEqual(receipt["outcome"], "UNKNOWN")
        self.assertIn("noncurrent_terminal_evidence", receipt["hold_reasons"])

    def test_later_pending_after_terminal_fails_closed(self):
        row = next(item for item in FIXTURES["valid"] if item["name"] == "later_pending_after_terminal_fails_closed")
        receipt = compile_record(row["record"])
        self.assertEqual(receipt["outcome"], "UNKNOWN")
        self.assertIn("later_pending_after_terminal", receipt["hold_reasons"])

    def test_future_capture_rejected(self):
        row = copy.deepcopy(FIXTURES["valid"][0]["record"])
        row["evidence"][0]["captured_at"] = "2026-09-18T00:00:00Z"
        with self.assertRaisesRegex(OutcomeError, "later than compiled_at"):
            compile_record(row)

    def test_capture_before_observation_rejected(self):
        row = copy.deepcopy(FIXTURES["valid"][0]["record"])
        row["evidence"][0]["captured_at"] = "2026-09-17T01:00:00Z"
        with self.assertRaisesRegex(OutcomeError, "precedes observed_at"):
            compile_record(row)

    def test_unknown_field_rejected(self):
        row = copy.deepcopy(FIXTURES["valid"][0]["record"])
        row["evidence"][0]["buyer_email"] = "not-allowed@example.invalid"
        with self.assertRaisesRegex(OutcomeError, "unknown fields"):
            compile_record(row)

    def test_rationale_email_url_and_phone_like_data_rejected(self):
        base = copy.deepcopy(FIXTURES["valid"][0]["record"])
        for text, fragment in [
            ("Contact buyer@example.invalid", "email address"),
            ("See https://example.invalid/debrief", "URL"),
            ("Call 212-555-0123", "phone-like"),
        ]:
            row = copy.deepcopy(base)
            row["evidence"][0]["rationale"] = {"status": "STATED", "text": text}
            with self.subTest(text=text):
                with self.assertRaisesRegex(OutcomeError, fragment):
                    compile_record(row)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(OutcomeError, "duplicate JSON object key"):
            loads_strict('{"schema":"x","schema":"y"}')

    def test_tampered_receipt_fails_verification(self):
        row = copy.deepcopy(FIXTURES["valid"][1]["record"])
        receipt = compile_record(row)
        receipt["outcome"] = "WON"
        with self.assertRaisesRegex(VerificationError, "receipt_sha256 mismatch"):
            verify_record(row, receipt)

    def test_rehashed_semantic_tamper_still_fails(self):
        from tools.procurement_win_loss.compiler import digest
        row = copy.deepcopy(FIXTURES["valid"][1]["record"])
        receipt = compile_record(row)
        receipt["outcome"] = "WON"
        receipt.pop("receipt_sha256")
        receipt["receipt_sha256"] = digest(receipt)
        with self.assertRaisesRegex(VerificationError, "semantic outcome mismatch"):
            verify_record(row, receipt)

    def test_authority_cannot_be_rehashed_true(self):
        from tools.procurement_win_loss.compiler import digest
        row = copy.deepcopy(FIXTURES["valid"][1]["record"])
        receipt = compile_record(row)
        receipt["authority"]["buyer_contact_authorized"] = True
        receipt.pop("receipt_sha256")
        receipt["receipt_sha256"] = digest(receipt)
        with self.assertRaisesRegex(VerificationError, "authority boundary mismatch"):
            verify_record(row, receipt)

    def test_input_tamper_after_receipt_fails(self):
        row = copy.deepcopy(FIXTURES["valid"][1]["record"])
        receipt = compile_record(row)
        row["opportunity_id"] = "SYNTH-RFP-TAMPER"
        row["evidence"][0]["bound_opportunity_id"] = "SYNTH-RFP-TAMPER"
        with self.assertRaisesRegex(VerificationError, "opportunity_id mismatch"):
            verify_record(row, receipt)

    def test_compiler_is_deterministic(self):
        row = copy.deepcopy(FIXTURES["valid"][1]["record"])
        self.assertEqual(compile_record(row), compile_record(row))

    def test_optimized_subprocess_keeps_runtime_validation(self):
        code = (
            "import copy\n"
            "from tools.procurement_win_loss.compiler import OutcomeError, compile_record\n"
            "from test_procurement_win_loss import FIXTURES\n"
            "row=copy.deepcopy(FIXTURES['valid'][0]['record'])\n"
            "row['evidence'][0]['redacted']=False\n"
            "try:\n"
            "    compile_record(row)\n"
            "except OutcomeError:\n"
            "    raise SystemExit(0)\n"
            "raise SystemExit(9)\n"
        )
        completed = subprocess.run(
            [sys.executable, "-O", "-c", code],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
