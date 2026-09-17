from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools.procurement_loss_remediation import (
    RemediationError,
    RemediationVerificationError,
    compile_plan,
    verify_plan,
)
from tools.procurement_win_loss import compile_record

ROOT = Path(__file__).resolve().parent
FIXTURES = json.loads(
    (ROOT / "tools" / "procurement_loss_remediation" / "fixtures.json").read_text()
)


def packet(name: str) -> dict:
    fixture = copy.deepcopy(FIXTURES[name])
    source = fixture.pop("outcome_record")
    return {
        "schema": "procurement-loss-remediation-input/v1",
        "outcome_record": source,
        "outcome_receipt": compile_record(source),
        **fixture,
    }


class ProcurementLossRemediationTests(unittest.TestCase):
    def test_stated_buyer_reason_produces_actionable_gap(self):
        receipt = compile_plan(packet("stated_loss"))
        self.assertEqual(receipt["source_outcome"], "LOST")
        self.assertEqual(receipt["status"], "ACTIONABLE_GAPS")
        self.assertEqual(len(receipt["source_evidence"]), 1)
        source = receipt["source_evidence"][0]
        self.assertEqual(source["evidence_id"], "notice-001")
        self.assertEqual(source["source_digest_sha256"], "1" * 64)
        self.assertEqual(source["observed_at"], "2026-09-17T11:00:00Z")
        self.assertEqual(source["evidence_status"], "CURRENT")
        self.assertEqual(len(receipt["buyer_reasons"]), 1)
        reason = receipt["buyer_reasons"][0]
        self.assertEqual(reason["statement_attribution"], "BUYER_STATED_SOURCE_BOUND")
        self.assertEqual(reason["category_attribution"], "OPERATOR_TAXONOMY_CLASSIFICATION")
        self.assertEqual(reason["category"], "QUALIFICATION_EVIDENCE")
        self.assertTrue(receipt["remediation_gaps"][0]["basis_valid"])
        self.assertTrue(all(value is False for value in receipt["authority"].values()))

    def test_receipt_verifier_accepts_exact_packet(self):
        raw = packet("stated_loss")
        receipt = compile_plan(raw)
        result = verify_plan(raw, receipt)
        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(result["remediation_status"], "ACTIONABLE_GAPS")

    def test_unknown_buyer_reason_can_support_only_internal_hypothesis_gap(self):
        receipt = compile_plan(packet("unknown_reason_internal_hypothesis"))
        self.assertEqual(receipt["source_outcome"], "LOST")
        self.assertEqual(receipt["status"], "ACTIONABLE_GAPS")
        self.assertEqual(receipt["buyer_reasons"], [])
        self.assertEqual(
            receipt["internal_hypotheses"][0]["attribution"],
            "INTERNAL_HYPOTHESIS_NOT_BUYER_FACT",
        )
        self.assertTrue(receipt["remediation_gaps"][0]["basis_valid"])

    def test_pending_source_holds_before_remediation(self):
        receipt = compile_plan(packet("pending_source"))
        self.assertEqual(receipt["source_outcome"], "UNKNOWN")
        self.assertEqual(receipt["status"], "HOLD_SOURCE")

    def test_source_stated_reason_requires_explicit_taxonomy_binding(self):
        raw = packet("stated_loss")
        raw["buyer_reason_mappings"] = []
        receipt = compile_plan(raw)
        self.assertEqual(receipt["status"], "HOLD_UNATTRIBUTED_REASON")
        self.assertEqual(receipt["unattributed_source_statement_ids"], ["notice-001"])
        self.assertIn("source_rationale_requires_category_binding", receipt["hold_reasons"])

    def test_wrong_reason_digest_holds_contradiction(self):
        raw = packet("stated_loss")
        raw["buyer_reason_mappings"][0]["source_digest_sha256"] = "9" * 64
        receipt = compile_plan(raw)
        self.assertEqual(receipt["status"], "HOLD_CONTRADICTION")
        self.assertTrue(
            any(reason.startswith("buyer_reason_source_digest_mismatch:") for reason in receipt["hold_reasons"])
        )

    def test_same_source_statement_cannot_be_classified_twice(self):
        raw = packet("stated_loss")
        duplicate = copy.deepcopy(raw["buyer_reason_mappings"][0])
        duplicate["reason_id"] = "second-label"
        duplicate["category"] = "OTHER_STATED"
        raw["buyer_reason_mappings"].append(duplicate)
        receipt = compile_plan(raw)
        self.assertEqual(receipt["status"], "HOLD_CONTRADICTION")
        self.assertTrue(
            any(reason.startswith("buyer_reason_evidence_mapped_more_than_once:") for reason in receipt["hold_reasons"])
        )

    def test_hypothesis_must_reference_retained_source_evidence(self):
        raw = packet("unknown_reason_internal_hypothesis")
        raw["internal_hypotheses"][0]["evidence_ids"] = ["not-in-source"]
        receipt = compile_plan(raw)
        self.assertEqual(receipt["status"], "HOLD_CONTRADICTION")
        self.assertIn("hypothesis_unknown_evidence:hyp-runway", receipt["hold_reasons"])

    def test_gap_cannot_cross_to_unknown_basis(self):
        raw = packet("unknown_reason_internal_hypothesis")
        raw["remediation_gaps"][0]["basis_id"] = "invented-buyer-reason"
        receipt = compile_plan(raw)
        self.assertEqual(receipt["status"], "HOLD_CONTRADICTION")
        self.assertFalse(receipt["remediation_gaps"][0]["basis_valid"])

    def test_coherent_source_with_no_gap_is_no_actionable_gap(self):
        raw = packet("stated_loss")
        raw["remediation_gaps"] = []
        receipt = compile_plan(raw)
        self.assertEqual(receipt["status"], "NO_ACTIONABLE_GAP")

    def test_private_locator_shaped_hypothesis_is_rejected(self):
        raw = packet("unknown_reason_internal_hypothesis")
        raw["internal_hypotheses"][0]["text"] = "Ask operator@example.com whether pursuit runway mattered."
        with self.assertRaisesRegex(RemediationError, "contact/locator-shaped"):
            compile_plan(raw)

    def test_private_locator_shaped_action_is_rejected(self):
        raw = packet("unknown_reason_internal_hypothesis")
        raw["remediation_gaps"][0]["action"] = "Call 555-123-4567 before scoring the next pursuit."
        with self.assertRaisesRegex(RemediationError, "contact/locator-shaped"):
            compile_plan(raw)

    def test_bool_is_not_a_gap_version(self):
        raw = packet("stated_loss")
        raw["remediation_gaps"][0]["version"] = True
        with self.assertRaisesRegex(RemediationError, "positive bounded integer"):
            compile_plan(raw)

    def test_tampered_source_outcome_receipt_is_rejected(self):
        raw = packet("stated_loss")
        raw["outcome_receipt"]["outcome"] = "WON"
        with self.assertRaisesRegex(RemediationError, "source outcome receipt failed verification"):
            compile_plan(raw)

    def test_tampered_remediation_receipt_is_rejected(self):
        raw = packet("stated_loss")
        receipt = compile_plan(raw)
        receipt["source_evidence"][0]["evidence_status"] = "WITHDRAWN"
        with self.assertRaises(RemediationVerificationError):
            verify_plan(raw, receipt)

    def test_order_invariance_includes_source_evidence_order(self):
        left = packet("stated_loss")
        second = {
            "evidence_id": "notice-001b",
            "bound_opportunity_id": "SYNTH-LOSS-001",
            "source_kind": "OWNER_LEDGER",
            "source_digest_sha256": "4" * 64,
            "observed_at": "2026-09-17T10:30:00Z",
            "captured_at": "2026-09-17T10:35:00Z",
            "evidence_status": "CURRENT",
            "redacted": True,
            "decision_signal": "NOT_SELECTED",
            "rationale": {"status": "UNKNOWN"},
        }
        left["outcome_record"]["evidence"].append(second)
        left["outcome_receipt"] = compile_record(left["outcome_record"])
        left["internal_hypotheses"] = [
            {
                "hypothesis_id": "hyp-secondary",
                "text": "A retained internal signal may justify a separate qualification experiment.",
                "confidence": "LOW",
                "evidence_ids": ["notice-001b"],
            }
        ]
        left["remediation_gaps"].append(
            {
                "gap_id": "gap-secondary",
                "version": 1,
                "gap_kind": "PROCESS",
                "rail": "DELIVERY_PROCESS",
                "basis_type": "INTERNAL_HYPOTHESIS",
                "basis_id": "hyp-secondary",
                "action": "Run a separate evidence-collection experiment before changing targeting policy.",
            }
        )

        right = copy.deepcopy(left)
        right["outcome_record"]["evidence"].reverse()
        right["outcome_receipt"] = compile_record(right["outcome_record"])
        right["buyer_reason_mappings"].reverse()
        right["internal_hypotheses"].reverse()
        right["remediation_gaps"].reverse()
        self.assertEqual(compile_plan(left), compile_plan(right))


if __name__ == "__main__":
    unittest.main()
