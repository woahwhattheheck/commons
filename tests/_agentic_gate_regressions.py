from __future__ import annotations

import os
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

from revenue.agentic_genai_evaluation_gate import cli
from revenue.agentic_genai_evaluation_gate.gate import (
    DECISION_HOLD,
    EvidenceError,
    verify_receipt,
)
from ._agentic_gate_base import AgenticGateCase, EVAL_AT


class AgenticGateV2RegressionTests(AgenticGateCase):
    def test_future_evidence_hold_cannot_promote_when_time_catches_up(self):
        packet = self.packet()
        future = "2026-09-13T14:05:00Z"
        for scenario in packet["scenarios"]:
            scenario["evidence_at"] = future
            scenario["automated_result"]["observed_at"] = future
            scenario["human_review"]["decided_at"] = future
            scenario["safety"]["observed_at"] = future
            scenario["observability"]["observed_at"] = future
        receipt = self.compile(packet)
        self.assertEqual(receipt["decision"], DECISION_HOLD)
        self.assertIn("FUTURE_EVIDENCE", receipt["reason_codes"])

        result = verify_receipt(
            packet,
            receipt,
            verified_at=EVAL_AT + timedelta(minutes=10),
        )
        self.assertFalse(result["valid"])
        self.assertTrue(result["integrity_valid"])
        self.assertEqual(result["reason"], "HISTORICAL_RECEIPT_HOLD")
        self.assertEqual(result["current_reason_codes"], [])


class AgenticGenAICliFinalFenceTests(unittest.TestCase):
    def test_same_inode_same_size_mutation_is_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "receipt.json"
            original_revalidate = cli._revalidate_target
            attacked = False

            def hostile_revalidate(target, *, final):
                nonlocal attacked
                if final and not attacked:
                    attacked = True
                    with output.open("r+b", buffering=0) as writer:
                        writer.seek(0)
                        writer.write(b"evil")
                        writer.flush()
                        os.fsync(writer.fileno())
                return original_revalidate(target, final=final)

            with mock.patch.object(
                cli,
                "_revalidate_target",
                side_effect=hostile_revalidate,
            ):
                with self.assertRaisesRegex(
                    EvidenceError,
                    "generation changed|published bytes differ",
                ):
                    cli._publish_exclusive([(output, b"ours")])
            self.assertEqual(output.read_bytes(), b"evil")

    def test_foreign_hardlink_is_detected_and_not_deleted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "receipt.json"
            foreign_link = root / "foreign-link.json"
            original_revalidate = cli._revalidate_target
            attacked = False

            def hostile_revalidate(target, *, final):
                nonlocal attacked
                if final and not attacked:
                    attacked = True
                    os.link(output, foreign_link)
                return original_revalidate(target, final=final)

            with mock.patch.object(
                cli,
                "_revalidate_target",
                side_effect=hostile_revalidate,
            ):
                with self.assertRaisesRegex(EvidenceError, "link count"):
                    cli._publish_exclusive([(output, b"ours")])
            self.assertEqual(output.read_bytes(), b"ours")
            self.assertEqual(foreign_link.read_bytes(), b"ours")
