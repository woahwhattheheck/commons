from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from revenue.agentic_genai_evaluation_gate import cli
from revenue.agentic_genai_evaluation_gate.gate import (
    DECISION_HOLD,
    DECISION_RELEASE,
    EvidenceError,
    compile_receipt,
    render_markdown,
    verify_receipt,
)
from revenue.agentic_genai_evaluation_gate.golden import build_golden_packet
from ._agentic_gate_base import AgenticGateCase, EVAL_AT


class AgenticGenAIEvaluationGateTestsPart3(AgenticGateCase):
    def test_automated_failure_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["automated_result"]["status"] = "FAIL"
        self.assertIn(
            "AUTOMATED_EVALUATION_FAILED",
            self.compile(packet)["reason_codes"],
        )

    def test_missing_required_human_review_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["human_review"] = None
        self.assertIn(
            "HUMAN_REVIEW_MISSING",
            self.compile(packet)["reason_codes"],
        )

    def test_human_failure_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["human_review"]["decision"] = "FAIL"
        self.assertIn(
            "HUMAN_REVIEW_FAILED",
            self.compile(packet)["reason_codes"],
        )

    def test_safety_unknown_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["safety"]["status"] = "UNKNOWN"
        self.assertIn(
            "SAFETY_UNKNOWN",
            self.compile(packet)["reason_codes"],
        )

    def test_safety_failure_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["safety"]["status"] = "FAIL"
        self.assertIn(
            "SAFETY_FAILED",
            self.compile(packet)["reason_codes"],
        )

    def test_observability_degraded_holds_when_required(self):
        packet = self.packet()
        packet["scenarios"][135]["observability"]["status"] = "DEGRADED"
        self.assertIn(
            "OBSERVABILITY_INCOMPLETE",
            self.compile(packet)["reason_codes"],
        )

    def test_unknown_tool_result_holds(self):
        packet = self.packet()
        packet["scenarios"][45]["tool_calls"][0][
            "result_status"
        ] = "UNKNOWN"
        self.assertIn(
            "TOOL_RESULT_UNKNOWN",
            self.compile(packet)["reason_codes"],
        )

    def test_failed_tool_result_holds(self):
        packet = self.packet()
        packet["scenarios"][45]["tool_calls"][0][
            "result_status"
        ] = "FAILURE"
        self.assertIn(
            "TOOL_RESULT_FAILED",
            self.compile(packet)["reason_codes"],
        )

    def test_bool_is_not_integer_score(self):
        packet = self.packet()
        packet["scenarios"][0]["automated_result"]["score_bps"] = True
        with self.assertRaises(EvidenceError):
            self.compile(packet)

    def test_bool_is_not_generation(self):
        packet = self.packet()
        packet["rubric"]["generation"] = True
        with self.assertRaises(EvidenceError):
            self.compile(packet)

    def test_float_score_rejected(self):
        packet = self.packet()
        packet["scenarios"][0]["automated_result"]["score_bps"] = 9500.0
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

    def test_schema_v1_rejected(self):
        packet = self.packet()
        packet["schema_version"] = 1
        with self.assertRaises(EvidenceError):
            self.compile(packet)

    def test_duplicate_tool_call_id_rejected(self):
        packet = self.packet()
        target = packet["scenarios"][90]
        target["tool_calls"].append(
            copy.deepcopy(target["tool_calls"][0])
        )
        with self.assertRaises(EvidenceError):
            self.compile(packet)

    def test_unknown_tool_effect_rejected(self):
        packet = self.packet()
        packet["scenarios"][45]["tool_calls"][0][
            "effect_class"
        ] = "TRANSFER_FUNDS"
        with self.assertRaises(EvidenceError):
            self.compile(packet)

    def test_noncanonical_timestamp_rejected(self):
        packet = self.packet()
        packet["scenarios"][0][
            "evidence_at"
        ] = "2026-09-13T13:45:00.000Z"
        with self.assertRaises(EvidenceError):
            self.compile(packet)

    def test_wrong_timestamp_offset_rejected(self):
        packet = self.packet()
        packet["scenarios"][0][
            "evidence_at"
        ] = "2026-09-13T09:45:00-04:00"
        with self.assertRaises(EvidenceError):
            self.compile(packet)

    def test_naive_evaluation_instant_rejected(self):
        with self.assertRaises(EvidenceError):
            self.compile(at=datetime(2026, 9, 13, 14, 0, 0))

    def test_reason_order_is_stable(self):
        packet = self.packet()
        packet["scenarios"][0]["automated_result"]["status"] = "FAIL"
        packet["scenarios"][0]["safety"]["status"] = "UNKNOWN"
        packet["scenarios"][0]["observability"]["status"] = "MISSING"
        receipt = self.compile(packet)
        self.assertEqual(
            receipt["reason_codes"],
            [
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
        packet["evaluation_id"] = (
            "synthetic-caterpillar-agentic-eval-20260913-v2"
        )
        second = self.compile(packet)
        self.assertNotEqual(
            first["receipt_sha256"],
            second["receipt_sha256"],
        )

    def test_malformed_receipt_is_rejected(self):
        result = verify_receipt(
            self.packet(),
            ["not", "an", "object"],
            verified_at=EVAL_AT,
        )
        self.assertEqual(result["reason"], "RECEIPT_NOT_OBJECT")
        self.assertFalse(result["integrity_valid"])

    def test_verifier_rejects_bad_claimed_timestamp(self):
        receipt = self.compile()
        receipt["evaluated_at"] = "not-a-time"
        result = verify_receipt(
            self.packet(),
            receipt,
            verified_at=EVAL_AT,
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "MALFORMED_EVIDENCE")

    def test_disable_human_requirement_allows_absent_review(self):
        packet = self.packet()
        packet["policy"]["require_human_review"] = False
        packet["scenarios"][0]["human_review"] = None
        self.assertEqual(
            self.compile(packet)["decision"],
            DECISION_RELEASE,
        )

    def test_disable_complete_observability_allows_degraded(self):
        packet = self.packet()
        packet["policy"]["require_complete_observability"] = False
        packet["scenarios"][135]["observability"]["status"] = "DEGRADED"
        self.assertEqual(
            self.compile(packet)["decision"],
            DECISION_RELEASE,
        )
