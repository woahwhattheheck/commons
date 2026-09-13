from __future__ import annotations

import copy
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from revenue.agentic_genai_evaluation_gate.gate import (
    DECISION_HOLD,
    DECISION_RELEASE,
    EvidenceError,
    compile_receipt,
    render_markdown,
    verify_receipt,
)
from revenue.agentic_genai_evaluation_gate.golden import build_golden_packet
from revenue.agentic_genai_evaluation_gate.cli import _read_bytes_bounded, _read_json


EVAL_AT = datetime(2026, 9, 13, 14, 0, 0, tzinfo=timezone.utc)


class AgenticGenAIEvaluationGateTests(unittest.TestCase):
    def packet(self):
        return build_golden_packet()

    def compile(self, packet=None):
        return compile_receipt(packet or self.packet(), evaluated_at=EVAL_AT)

    def test_golden_180_scenario_release_candidate(self):
        receipt = self.compile()
        self.assertEqual(receipt["decision"], DECISION_RELEASE)
        self.assertEqual(receipt["scenario_count"], 180)
        self.assertEqual(
            receipt["category_counts"],
            {
                "ADVERSARIAL": 45,
                "DEGRADED_OBSERVABILITY": 45,
                "NORMAL": 45,
                "TOOL_USING": 45,
            },
        )
        self.assertEqual(receipt["tool_call_count"], 135)
        self.assertEqual(receipt["external_side_effect_call_count"], 45)
        self.assertEqual(receipt["reason_codes"], [])
        self.assertFalse(any(receipt["authority"].values()))

    def test_deterministic_same_instant(self):
        self.assertEqual(self.compile(), self.compile())

    def test_scenario_order_normalized(self):
        packet = self.packet()
        packet["scenarios"].reverse()
        self.assertEqual(self.compile(packet), self.compile())

    def test_required_scenario_order_normalized(self):
        packet = self.packet()
        packet["evaluation_set"]["required_scenarios"].reverse()
        self.assertEqual(self.compile(packet), self.compile())

    def test_tool_call_order_normalized(self):
        packet = self.packet()
        target = packet["scenarios"][90]
        target["tool_calls"].reverse()
        self.assertEqual(self.compile(packet), self.compile())

    def test_verify_exact_receipt(self):
        packet = self.packet()
        receipt = self.compile(packet)
        result = verify_receipt(packet, receipt, verified_at=EVAL_AT + timedelta(seconds=1))
        self.assertTrue(result["valid"])
        self.assertEqual(result["decision"], DECISION_RELEASE)

    def test_receipt_tamper_rejected(self):
        packet = self.packet()
        receipt = self.compile(packet)
        receipt["scenario_count"] = 179
        result = verify_receipt(packet, receipt, verified_at=EVAL_AT)
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "RECEIPT_MISMATCH")

    def test_packet_tamper_rejected_against_old_receipt(self):
        packet = self.packet()
        receipt = self.compile(packet)
        packet["scenarios"][0]["result_sha256"] = "f" * 64
        result = verify_receipt(packet, receipt, verified_at=EVAL_AT)
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "RECEIPT_MISMATCH")


    def test_automated_result_binding_tamper_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["automated_score_bps"] -= 1
        receipt = self.compile(packet)
        self.assertEqual(receipt["decision"], DECISION_HOLD)
        self.assertIn("AUTOMATED_RESULT_BINDING_MISMATCH", receipt["reason_codes"])

    def test_fresh_result_transplant_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["result_sha256"] = packet["scenarios"][1]["result_sha256"]
        receipt = self.compile(packet)
        self.assertEqual(receipt["decision"], DECISION_HOLD)
        self.assertIn("RESULT_BINDING_MISMATCH", receipt["reason_codes"])

    def test_current_verification_reassesses_stale_evidence(self):
        packet = self.packet()
        packet["policy"]["max_evidence_age_seconds"] = 3600
        receipt = compile_receipt(packet, evaluated_at=EVAL_AT)
        self.assertEqual(receipt["decision"], DECISION_RELEASE)
        result = verify_receipt(packet, receipt, verified_at=EVAL_AT + timedelta(hours=1, seconds=1))
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "CURRENT_EVIDENCE_HOLD")
        self.assertEqual(result["decision"], DECISION_HOLD)
        self.assertIn("STALE_EVIDENCE", result["reason_codes"])

    def test_future_receipt_rejected(self):
        packet = self.packet()
        receipt = compile_receipt(packet, evaluated_at=EVAL_AT + timedelta(minutes=5))
        result = verify_receipt(packet, receipt, verified_at=EVAL_AT)
        self.assertEqual(result, {"valid": False, "reason": "RECEIPT_FROM_FUTURE"})

    def test_missing_required_scenario_holds(self):
        packet = self.packet()
        packet["scenarios"].pop()
        receipt = self.compile(packet)
        self.assertEqual(receipt["decision"], DECISION_HOLD)
        self.assertIn("SCENARIO_UNIVERSE_MISMATCH", receipt["reason_codes"])

    def test_extra_scenario_holds(self):
        packet = self.packet()
        extra = copy.deepcopy(packet["scenarios"][0])
        extra["scenario_id"] = "scenario-extra"
        extra["human_review"]["review_id"] = "review-extra"
        packet["scenarios"].append(extra)
        receipt = self.compile(packet)
        self.assertIn("SCENARIO_UNIVERSE_MISMATCH", receipt["reason_codes"])

    def test_duplicate_scenario_holds(self):
        packet = self.packet()
        packet["scenarios"][-1]["scenario_id"] = packet["scenarios"][0]["scenario_id"]
        receipt = self.compile(packet)
        self.assertIn("DUPLICATE_SCENARIO_ID", receipt["reason_codes"])
        self.assertIn("SCENARIO_UNIVERSE_MISMATCH", receipt["reason_codes"])

    def test_scenario_build_transplant_holds(self):
        packet = self.packet()
        packet["scenarios"][3]["agent_build_sha256"] = "a" * 64
        receipt = self.compile(packet)
        self.assertIn("AGENT_BUILD_MISMATCH", receipt["reason_codes"])

    def test_review_build_transplant_holds(self):
        packet = self.packet()
        packet["scenarios"][3]["human_review"]["agent_build_sha256"] = "a" * 64
        self.assertIn("AGENT_BUILD_MISMATCH", self.compile(packet)["reason_codes"])

    def test_rubric_transplant_holds(self):
        packet = self.packet()
        packet["scenarios"][3]["rubric_sha256"] = "b" * 64
        self.assertIn("RUBRIC_MISMATCH", self.compile(packet)["reason_codes"])

    def test_trace_transplant_holds(self):
        packet = self.packet()
        packet["scenarios"][90]["human_review"]["trace_sha256"] = "c" * 64
        self.assertIn("TRACE_BINDING_MISMATCH", self.compile(packet)["reason_codes"])

    def test_tool_trace_transplant_holds(self):
        packet = self.packet()
        packet["scenarios"][45]["tool_calls"][0]["trace_sha256"] = "d" * 64
        self.assertIn("TRACE_BINDING_MISMATCH", self.compile(packet)["reason_codes"])

    def test_stale_evidence_holds(self):
        packet = self.packet()
        packet["policy"]["max_evidence_age_seconds"] = 3600
        packet["scenarios"][0]["human_review"]["decided_at"] = "2026-09-13T12:00:00Z"
        self.assertIn("STALE_EVIDENCE", self.compile(packet)["reason_codes"])

    def test_future_evidence_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["safety"]["observed_at"] = "2026-09-13T14:00:01Z"
        self.assertIn("FUTURE_EVIDENCE", self.compile(packet)["reason_codes"])

    def test_below_threshold_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["automated_score_bps"] = 8999
        self.assertIn("AUTOMATED_SCORE_BELOW_THRESHOLD", self.compile(packet)["reason_codes"])

    def test_automated_failure_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["automated_status"] = "FAIL"
        self.assertIn("AUTOMATED_EVALUATION_FAILED", self.compile(packet)["reason_codes"])

    def test_missing_required_human_review_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["human_review"] = None
        self.assertIn("HUMAN_REVIEW_MISSING", self.compile(packet)["reason_codes"])

    def test_human_failure_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["human_review"]["decision"] = "FAIL"
        self.assertIn("HUMAN_REVIEW_FAILED", self.compile(packet)["reason_codes"])

    def test_safety_unknown_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["safety"]["status"] = "UNKNOWN"
        self.assertIn("SAFETY_UNKNOWN", self.compile(packet)["reason_codes"])

    def test_safety_failure_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["safety"]["status"] = "FAIL"
        self.assertIn("SAFETY_FAILED", self.compile(packet)["reason_codes"])

    def test_observability_degraded_holds_when_required(self):
        packet = self.packet()
        packet["scenarios"][135]["observability"]["status"] = "DEGRADED"
        self.assertIn("OBSERVABILITY_INCOMPLETE", self.compile(packet)["reason_codes"])

    def test_unknown_tool_result_holds(self):
        packet = self.packet()
        packet["scenarios"][45]["tool_calls"][0]["result_status"] = "UNKNOWN"
        self.assertIn("TOOL_RESULT_UNKNOWN", self.compile(packet)["reason_codes"])

    def test_failed_tool_result_holds(self):
        packet = self.packet()
        packet["scenarios"][45]["tool_calls"][0]["result_status"] = "FAILURE"
        self.assertIn("TOOL_RESULT_FAILED", self.compile(packet)["reason_codes"])

    def test_bool_is_not_integer_score(self):
        packet = self.packet()
        packet["scenarios"][0]["automated_score_bps"] = True
        with self.assertRaises(EvidenceError):
            self.compile(packet)

    def test_bool_is_not_generation(self):
        packet = self.packet()
        packet["rubric"]["generation"] = True
        with self.assertRaises(EvidenceError):
            self.compile(packet)

    def test_float_score_rejected(self):
        packet = self.packet()
        packet["scenarios"][0]["automated_score_bps"] = 9500.0
        with self.assertRaises(EvidenceError):
            self.compile(packet)

    def test_unknown_top_level_key_rejected(self):
        packet = self.packet()
        packet["caller_override"] = "release"
        with self.assertRaises(EvidenceError):
            self.compile(packet)

    def test_unknown_nested_key_rejected(self):
        packet = self.packet()
        packet["scenarios"][0]["safety"]["release_authorized"] = True
        with self.assertRaises(EvidenceError):
            self.compile(packet)

    def test_duplicate_tool_call_id_rejected(self):
        packet = self.packet()
        target = packet["scenarios"][90]
        target["tool_calls"].append(copy.deepcopy(target["tool_calls"][0]))
        with self.assertRaises(EvidenceError):
            self.compile(packet)

    def test_unknown_tool_effect_rejected(self):
        packet = self.packet()
        packet["scenarios"][45]["tool_calls"][0]["effect_class"] = "TRANSFER_FUNDS"
        with self.assertRaises(EvidenceError):
            self.compile(packet)

    def test_noncanonical_timestamp_rejected(self):
        packet = self.packet()
        packet["scenarios"][0]["evidence_at"] = "2026-09-13T13:45:00.000Z"
        with self.assertRaises(EvidenceError):
            self.compile(packet)

    def test_wrong_timestamp_offset_rejected(self):
        packet = self.packet()
        packet["scenarios"][0]["evidence_at"] = "2026-09-13T09:45:00-04:00"
        with self.assertRaises(EvidenceError):
            self.compile(packet)

    def test_cli_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.json"
            path.write_text('{"scenario_id":"a","scenario_id":"b"}', encoding="utf-8")
            with self.assertRaisesRegex(EvidenceError, "duplicate JSON key"):
                _read_json(path)

    def test_cli_rejects_changing_file_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "changing.json"
            path.write_bytes(b'{"value":1}')
            real_read = os.read
            mutated = False

            def read_then_mutate(fd, size):
                nonlocal mutated
                chunk = real_read(fd, size)
                if chunk and not mutated:
                    mutated = True
                    path.write_bytes(b'{"value":2}')
                return chunk

            with patch("revenue.agentic_genai_evaluation_gate.cli.os.read", side_effect=read_then_mutate):
                with self.assertRaisesRegex(EvidenceError, "file generation changed during read"):
                    _read_bytes_bounded(path)

    def test_cli_accepts_stable_file_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stable.json"
            path.write_text('{"value":1}', encoding="utf-8")
            self.assertEqual(_read_json(path), {"value": 1})

    def test_reason_order_is_stable(self):
        packet = self.packet()
        packet["scenarios"][0]["automated_status"] = "FAIL"
        packet["scenarios"][0]["safety"]["status"] = "UNKNOWN"
        packet["scenarios"][0]["observability"]["status"] = "MISSING"
        receipt = self.compile(packet)
        self.assertEqual(
            receipt["reason_codes"],
            [
                "AUTOMATED_RESULT_BINDING_MISMATCH",
                "AUTOMATED_EVALUATION_FAILED",
                "SAFETY_UNKNOWN",
                "OBSERVABILITY_INCOMPLETE",
            ],
        )

    def test_markdown_has_authority_warning(self):
        markdown = render_markdown(self.compile())
        self.assertIn("RELEASE_CANDIDATE", markdown)
        self.assertIn("authorizes no deployment", markdown)

    def test_receipt_self_hash_changes_if_semantics_change(self):
        first = self.compile()
        packet = self.packet()
        packet["evaluation_id"] = "synthetic-caterpillar-agentic-eval-20260913-v2"
        second = self.compile(packet)
        self.assertNotEqual(first["receipt_sha256"], second["receipt_sha256"])

    def test_malformed_receipt_is_rejected(self):
        result = verify_receipt(self.packet(), ["not", "an", "object"], verified_at=EVAL_AT)
        self.assertEqual(result, {"valid": False, "reason": "RECEIPT_NOT_OBJECT"})

    def test_verifier_rejects_bad_claimed_timestamp(self):
        receipt = self.compile()
        receipt["evaluated_at"] = "not-a-time"
        result = verify_receipt(self.packet(), receipt, verified_at=EVAL_AT)
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "MALFORMED_EVIDENCE")

    def test_disable_human_requirement_allows_absent_review(self):
        packet = self.packet()
        packet["policy"]["require_human_review"] = False
        packet["scenarios"][0]["human_review"] = None
        receipt = self.compile(packet)
        self.assertEqual(receipt["decision"], DECISION_RELEASE)

    def test_disable_complete_observability_requirement_allows_degraded(self):
        packet = self.packet()
        packet["policy"]["require_complete_observability"] = False
        packet["scenarios"][135]["observability"]["status"] = "DEGRADED"
        receipt = self.compile(packet)
        self.assertEqual(receipt["decision"], DECISION_RELEASE)


if __name__ == "__main__":
    unittest.main()
