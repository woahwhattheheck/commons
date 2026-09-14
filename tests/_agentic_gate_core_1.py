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


class AgenticGenAIEvaluationGateTestsPart1(AgenticGateCase):
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
        packet["scenarios"][90]["tool_calls"].reverse()
        self.assertEqual(self.compile(packet), self.compile())

    def test_verify_exact_current_receipt(self):
        packet = self.packet()
        receipt = self.compile(packet)
        result = verify_receipt(
            packet,
            receipt,
            verified_at=EVAL_AT + timedelta(seconds=1),
        )
        self.assertTrue(result["valid"])
        self.assertTrue(result["integrity_valid"])
        self.assertTrue(result["current_valid"])
        self.assertEqual(result["reason"], "VERIFIED_CURRENT")
        self.assertEqual(result["decision"], DECISION_RELEASE)

    def test_old_release_becomes_current_hold_after_expiry(self):
        packet = self.packet()
        packet["policy"]["max_evidence_age_seconds"] = 3600
        receipt = self.compile(packet)
        result = verify_receipt(
            packet,
            receipt,
            verified_at=EVAL_AT + timedelta(hours=2),
        )
        self.assertFalse(result["valid"])
        self.assertTrue(result["integrity_valid"])
        self.assertFalse(result["current_valid"])
        self.assertEqual(result["reason"], "CURRENT_EVIDENCE_HOLD")
        self.assertEqual(result["decision"], DECISION_HOLD)
        self.assertIn("STALE_EVIDENCE", result["current_reason_codes"])

    def test_historical_hold_never_promotes_without_new_receipt(self):
        packet = self.packet()
        packet["scenarios"][0]["automated_result"]["status"] = "FAIL"
        receipt = self.compile(packet)
        result = verify_receipt(packet, receipt, verified_at=EVAL_AT)
        self.assertFalse(result["valid"])
        self.assertTrue(result["integrity_valid"])
        self.assertEqual(result["reason"], "HISTORICAL_RECEIPT_HOLD")
        self.assertEqual(result["decision"], DECISION_HOLD)

    def test_receipt_tamper_rejected(self):
        packet = self.packet()
        receipt = self.compile(packet)
        receipt["scenario_count"] = 179
        result = verify_receipt(packet, receipt, verified_at=EVAL_AT)
        self.assertFalse(result["valid"])
        self.assertFalse(result["integrity_valid"])
        self.assertEqual(result["reason"], "RECEIPT_MISMATCH")

    def test_packet_tamper_rejected_against_old_receipt(self):
        packet = self.packet()
        receipt = self.compile(packet)
        packet["scenarios"][0]["result_sha256"] = "f" * 64
        result = verify_receipt(packet, receipt, verified_at=EVAL_AT)
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "RECEIPT_MISMATCH")

    def test_future_receipt_rejected(self):
        packet = self.packet()
        receipt = self.compile(
            packet,
            at=EVAL_AT + timedelta(minutes=5),
        )
        result = verify_receipt(packet, receipt, verified_at=EVAL_AT)
        self.assertEqual(result["reason"], "RECEIPT_FROM_FUTURE")
        self.assertFalse(result["integrity_valid"])

    def test_missing_required_scenario_holds(self):
        packet = self.packet()
        packet["scenarios"].pop()
        receipt = self.compile(packet)
        self.assertEqual(receipt["decision"], DECISION_HOLD)
        self.assertIn(
            "SCENARIO_UNIVERSE_MISMATCH",
            receipt["reason_codes"],
        )

    def test_extra_scenario_holds(self):
        packet = self.packet()
        extra = copy.deepcopy(packet["scenarios"][0])
        extra["scenario_id"] = "scenario-extra"
        extra["human_review"]["review_id"] = "review-extra"
        packet["scenarios"].append(extra)
        self.assertIn(
            "SCENARIO_UNIVERSE_MISMATCH",
            self.compile(packet)["reason_codes"],
        )

    def test_duplicate_scenario_holds(self):
        packet = self.packet()
        packet["scenarios"][-1]["scenario_id"] = (
            packet["scenarios"][0]["scenario_id"]
        )
        reasons = self.compile(packet)["reason_codes"]
        self.assertIn("DUPLICATE_SCENARIO_ID", reasons)
        self.assertIn("SCENARIO_UNIVERSE_MISMATCH", reasons)

    def test_automated_scenario_transplant_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["automated_result"][
            "scenario_id"
        ] = packet["scenarios"][1]["scenario_id"]
        self.assertIn(
            "SCENARIO_BINDING_MISMATCH",
            self.compile(packet)["reason_codes"],
        )

    def test_human_scenario_transplant_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["human_review"][
            "scenario_id"
        ] = packet["scenarios"][1]["scenario_id"]
        self.assertIn(
            "SCENARIO_BINDING_MISMATCH",
            self.compile(packet)["reason_codes"],
        )

    def test_safety_scenario_transplant_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["safety"][
            "scenario_id"
        ] = packet["scenarios"][1]["scenario_id"]
        self.assertIn(
            "SCENARIO_BINDING_MISMATCH",
            self.compile(packet)["reason_codes"],
        )

    def test_observability_scenario_transplant_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["observability"][
            "scenario_id"
        ] = packet["scenarios"][1]["scenario_id"]
        self.assertIn(
            "SCENARIO_BINDING_MISMATCH",
            self.compile(packet)["reason_codes"],
        )
