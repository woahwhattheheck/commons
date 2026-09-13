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


class AgenticGenAIEvaluationGateTestsPart2(AgenticGateCase):
    def test_tool_scenario_transplant_holds(self):
        packet = self.packet()
        packet["scenarios"][45]["tool_calls"][0][
            "scenario_id"
        ] = packet["scenarios"][46]["scenario_id"]
        self.assertIn(
            "SCENARIO_BINDING_MISMATCH",
            self.compile(packet)["reason_codes"],
        )

    def test_whole_interpreting_evidence_transplant_holds(self):
        packet = self.packet()
        source = packet["scenarios"][1]
        target = packet["scenarios"][0]
        target["trace_sha256"] = source["trace_sha256"]
        target["result_sha256"] = source["result_sha256"]
        target["automated_result"] = copy.deepcopy(
            source["automated_result"]
        )
        target["human_review"] = copy.deepcopy(source["human_review"])
        target["human_review"]["review_id"] = "review-transplanted"
        target["safety"] = copy.deepcopy(source["safety"])
        target["observability"] = copy.deepcopy(source["observability"])
        target["tool_calls"] = copy.deepcopy(source["tool_calls"])
        self.assertIn(
            "SCENARIO_BINDING_MISMATCH",
            self.compile(packet)["reason_codes"],
        )

    def test_duplicate_review_id_across_scenarios_rejected(self):
        packet = self.packet()
        packet["scenarios"][1]["human_review"]["review_id"] = (
            packet["scenarios"][0]["human_review"]["review_id"]
        )
        with self.assertRaisesRegex(
            EvidenceError,
            "duplicate human review id",
        ):
            self.compile(packet)

    def test_duplicate_tool_call_id_across_scenarios_rejected(self):
        packet = self.packet()
        packet["scenarios"][46]["tool_calls"][0]["call_id"] = (
            packet["scenarios"][45]["tool_calls"][0]["call_id"]
        )
        with self.assertRaisesRegex(
            EvidenceError,
            "duplicate tool call id across scenarios",
        ):
            self.compile(packet)

    def test_scenario_build_transplant_holds(self):
        packet = self.packet()
        packet["scenarios"][3]["agent_build_sha256"] = "a" * 64
        self.assertIn(
            "AGENT_BUILD_MISMATCH",
            self.compile(packet)["reason_codes"],
        )

    def test_automated_build_transplant_holds(self):
        packet = self.packet()
        packet["scenarios"][3]["automated_result"][
            "agent_build_sha256"
        ] = "a" * 64
        self.assertIn(
            "AGENT_BUILD_MISMATCH",
            self.compile(packet)["reason_codes"],
        )

    def test_review_build_transplant_holds(self):
        packet = self.packet()
        packet["scenarios"][3]["human_review"][
            "agent_build_sha256"
        ] = "a" * 64
        self.assertIn(
            "AGENT_BUILD_MISMATCH",
            self.compile(packet)["reason_codes"],
        )

    def test_rubric_transplant_holds(self):
        packet = self.packet()
        packet["scenarios"][3]["rubric_sha256"] = "b" * 64
        self.assertIn(
            "RUBRIC_MISMATCH",
            self.compile(packet)["reason_codes"],
        )

    def test_trace_transplant_holds(self):
        packet = self.packet()
        packet["scenarios"][90]["human_review"]["trace_sha256"] = "c" * 64
        self.assertIn(
            "TRACE_BINDING_MISMATCH",
            self.compile(packet)["reason_codes"],
        )

    def test_tool_trace_transplant_holds(self):
        packet = self.packet()
        packet["scenarios"][45]["tool_calls"][0]["trace_sha256"] = "d" * 64
        self.assertIn(
            "TRACE_BINDING_MISMATCH",
            self.compile(packet)["reason_codes"],
        )

    def test_top_level_result_transplant_holds_fresh_compile(self):
        packet = self.packet()
        packet["scenarios"][0]["result_sha256"] = (
            packet["scenarios"][1]["result_sha256"]
        )
        receipt = self.compile(packet)
        self.assertEqual(receipt["decision"], DECISION_HOLD)
        self.assertIn(
            "RESULT_BINDING_MISMATCH",
            receipt["reason_codes"],
        )

    def test_arbitrary_valid_result_digest_holds_fresh_compile(self):
        packet = self.packet()
        packet["scenarios"][0]["result_sha256"] = "f" * 64
        self.assertIn(
            "RESULT_BINDING_MISMATCH",
            self.compile(packet)["reason_codes"],
        )

    def test_automated_result_binding_mismatch_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["automated_result"][
            "result_sha256"
        ] = "e" * 64
        self.assertIn(
            "RESULT_BINDING_MISMATCH",
            self.compile(packet)["reason_codes"],
        )

    def test_human_result_binding_mismatch_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["human_review"][
            "result_sha256"
        ] = "e" * 64
        self.assertIn(
            "RESULT_BINDING_MISMATCH",
            self.compile(packet)["reason_codes"],
        )

    def test_safety_result_binding_mismatch_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["safety"]["result_sha256"] = "e" * 64
        self.assertIn(
            "RESULT_BINDING_MISMATCH",
            self.compile(packet)["reason_codes"],
        )

    def test_observability_result_binding_mismatch_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["observability"][
            "result_sha256"
        ] = "e" * 64
        self.assertIn(
            "RESULT_BINDING_MISMATCH",
            self.compile(packet)["reason_codes"],
        )

    def test_tool_result_binding_mismatch_holds(self):
        packet = self.packet()
        packet["scenarios"][45]["tool_calls"][0][
            "result_sha256"
        ] = "e" * 64
        self.assertIn(
            "RESULT_BINDING_MISMATCH",
            self.compile(packet)["reason_codes"],
        )

    def test_stale_evidence_holds(self):
        packet = self.packet()
        packet["policy"]["max_evidence_age_seconds"] = 3600
        packet["scenarios"][0]["human_review"][
            "decided_at"
        ] = "2026-09-13T12:00:00Z"
        self.assertIn(
            "STALE_EVIDENCE",
            self.compile(packet)["reason_codes"],
        )

    def test_future_evidence_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["safety"][
            "observed_at"
        ] = "2026-09-13T14:00:01Z"
        self.assertIn(
            "FUTURE_EVIDENCE",
            self.compile(packet)["reason_codes"],
        )

    def test_below_threshold_holds(self):
        packet = self.packet()
        packet["scenarios"][0]["automated_result"]["score_bps"] = 8999
        self.assertIn(
            "AUTOMATED_SCORE_BELOW_THRESHOLD",
            self.compile(packet)["reason_codes"],
        )
