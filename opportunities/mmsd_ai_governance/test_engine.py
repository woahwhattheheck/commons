from __future__ import annotations

import copy
import unittest

from .acceptance import AS_OF, fixture
from .budget import BudgetError, validate_budget
from .engine import REQUIRED_GATES, PursuitError, evaluate, strict_json_loads, verify


def officialize(packet: dict) -> dict:
    p = copy.deepcopy(packet)
    p["sources"].append(
        {
            "source_id": "official-rfp-20260914",
            "doc_kind": "RFP",
            "generation": "2026-09-14",
            "authority": "OFFICIAL_BYTES",
            "source_ref": "madsewer.org:FINAL-RFP-Comprehensive-AI-Policy-Development-1.pdf",
            "content_sha256": "a" * 64,
            "captured_at": "2026-09-14T03:04:00Z",
            "current": True,
            "fetch_state": "AVAILABLE",
            "supersedes": None,
        }
    )
    p["source_set_complete"] = True
    p["addenda_checked"] = True
    p["qa_checked"] = True
    p["deadlines"]["proposal_due_source_id"] = "official-rfp-20260914"
    return p


def pass_route(packet: dict, route: str) -> None:
    for gate in packet["gates"]:
        if gate["route"] == route:
            gate["state"] = "PASS"
            gate["evidence_refs"] = [f"evidence-{route.lower()}-{gate['gate_id']}"]


class Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.p = fixture()

    def test_current_real_posture_is_source_refresh(self) -> None:
        out = evaluate(self.p, AS_OF)
        self.assertEqual(out["disposition"], "SOURCE_REFRESH_REQUIRED")
        self.assertFalse(out["source_posture"]["official_submission_bytes_complete"])
        self.assertFalse(out["deadlines"]["proposal_due_authoritative"])
        self.assertIn("buyer-page-probe-20260914", out["source_posture"]["current_unavailable_source_ids"])

    def test_cached_buyer_page_cannot_authorize_deadline(self) -> None:
        out = evaluate(self.p, AS_OF)
        self.assertFalse(out["deadlines"]["proposal_due_authoritative"])

    def test_current_404_official_page_cannot_authorize_deadline(self) -> None:
        self.p["deadlines"]["proposal_due_source_id"] = "buyer-page-probe-20260914"
        out = evaluate(self.p, AS_OF)
        self.assertFalse(out["deadlines"]["proposal_due_authoritative"])
        self.assertEqual(out["disposition"], "SOURCE_REFRESH_REQUIRED")

    def test_secondary_index_cannot_be_submission_bytes(self) -> None:
        self.p["source_set_complete"] = True
        self.p["addenda_checked"] = True
        self.p["qa_checked"] = True
        out = evaluate(self.p, AS_OF)
        self.assertFalse(out["source_posture"]["official_submission_bytes_complete"])
        self.assertEqual(out["disposition"], "SOURCE_REFRESH_REQUIRED")

    def test_official_bytes_move_to_team_partner_required(self) -> None:
        p = officialize(self.p)
        out = evaluate(p, AS_OF)
        self.assertEqual(out["disposition"], "TEAM_PARTNER_REQUIRED")
        self.assertTrue(out["source_posture"]["official_submission_bytes_complete"])
        self.assertTrue(out["deadlines"]["proposal_due_authoritative"])

    def test_missing_addenda_check_blocks_even_with_official_rfp(self) -> None:
        p = officialize(self.p)
        p["addenda_checked"] = False
        self.assertEqual(evaluate(p, AS_OF)["disposition"], "SOURCE_REFRESH_REQUIRED")

    def test_missing_qa_check_blocks_even_with_official_rfp(self) -> None:
        p = officialize(self.p)
        p["qa_checked"] = False
        self.assertEqual(evaluate(p, AS_OF)["disposition"], "SOURCE_REFRESH_REQUIRED")

    def test_team_can_build_only_after_confirmed_workshare_and_gates(self) -> None:
        p = officialize(self.p)
        pass_route(p, "TEAM")
        p["partner"] = {
            "candidate_id": "prime-one",
            "confirmed": True,
            "commercial_workshare_agreed": True,
            "evidence_refs": ["partner-reply-1"],
        }
        out = evaluate(p, AS_OF)
        self.assertEqual(out["disposition"], "TEAMING_RESPONSE_BUILD_READY")
        self.assertFalse(out["authority"]["may_submit"])

    def test_team_submission_review_requires_budget_and_owner_release(self) -> None:
        p = officialize(self.p)
        pass_route(p, "TEAM")
        p["partner"] = {
            "candidate_id": "prime-one",
            "confirmed": True,
            "commercial_workshare_agreed": True,
            "evidence_refs": ["partner-reply-1"],
        }
        p["budget"] = {
            "math_valid": True,
            "owner_approved": True,
            "pricing_structure_known": True,
            "total_cents": 12500000,
        }
        p["owner_release"] = True
        out = evaluate(p, AS_OF)
        self.assertEqual(out["disposition"], "TEAM_READY_FOR_OWNER_SUBMISSION_REVIEW")
        self.assertTrue(out["authority"]["may_submit"])
        self.assertFalse(out["authority"]["may_bind_contract"])
        self.assertFalse(out["authority"]["may_claim_award"])
        self.assertFalse(out["authority"]["may_claim_payment_or_revenue"])

    def test_prime_submission_review_does_not_require_partner(self) -> None:
        p = officialize(self.p)
        pass_route(p, "PRIME")
        p["budget"] = {
            "math_valid": True,
            "owner_approved": True,
            "pricing_structure_known": True,
            "total_cents": 11000000,
        }
        p["owner_release"] = True
        out = evaluate(p, AS_OF)
        self.assertEqual(out["disposition"], "PRIME_READY_FOR_OWNER_SUBMISSION_REVIEW")
        self.assertTrue(out["authority"]["may_submit"])

    def test_pass_gate_requires_evidence(self) -> None:
        self.p["gates"][0]["state"] = "PASS"
        with self.assertRaises(PursuitError):
            evaluate(self.p, AS_OF)

    def test_unknown_gate_cannot_satisfy_route(self) -> None:
        p = officialize(self.p)
        pass_route(p, "PRIME")
        gate = next(g for g in p["gates"] if g["route"] == "PRIME" and g["gate_id"] == "similar_references")
        gate["state"] = "HOLD"
        gate["evidence_refs"] = []
        p["budget"] = {
            "math_valid": True,
            "owner_approved": True,
            "pricing_structure_known": True,
            "total_cents": 1000000,
        }
        p["owner_release"] = True
        self.assertEqual(evaluate(p, AS_OF)["disposition"], "TEAM_PARTNER_REQUIRED")

    def test_workshare_cannot_precede_partner_confirmation(self) -> None:
        self.p["partner"]["commercial_workshare_agreed"] = True
        with self.assertRaises(PursuitError):
            evaluate(self.p, AS_OF)

    def test_confirmed_partner_requires_evidence(self) -> None:
        self.p["partner"] = {
            "candidate_id": "prime-one",
            "confirmed": True,
            "commercial_workshare_agreed": False,
            "evidence_refs": [],
        }
        with self.assertRaises(PursuitError):
            evaluate(self.p, AS_OF)

    def test_observed_outreach_requires_provider_receipt(self) -> None:
        self.p["outreach"]["state"] = "SENT_NOT_ACCEPTED"
        with self.assertRaises(PursuitError):
            evaluate(self.p, AS_OF)

    def test_sent_outreach_is_not_partner_confirmation(self) -> None:
        self.p["outreach"] = {"state": "SENT_NOT_ACCEPTED", "provider_receipt_id": "gmail-message-1"}
        out = evaluate(self.p, AS_OF)
        self.assertFalse(out["partner_posture"]["confirmed"])
        self.assertEqual(out["disposition"], "SOURCE_REFRESH_REQUIRED")

    def test_owner_cannot_approve_unknown_pricing(self) -> None:
        self.p["budget"] = {
            "math_valid": True,
            "owner_approved": True,
            "pricing_structure_known": False,
            "total_cents": 1,
        }
        with self.assertRaises(PursuitError):
            evaluate(self.p, AS_OF)

    def test_budget_bool_is_not_integer(self) -> None:
        self.p["budget"]["total_cents"] = True
        with self.assertRaises(PursuitError):
            evaluate(self.p, AS_OF)

    def test_future_source_fails(self) -> None:
        self.p["sources"][0]["captured_at"] = "2026-09-14T03:16:00Z"
        with self.assertRaises(PursuitError):
            evaluate(self.p, AS_OF)

    def test_changed_duplicate_source_id_fails(self) -> None:
        duplicate = copy.deepcopy(self.p["sources"][0])
        duplicate["source_ref"] = "changed:transport"
        self.p["sources"].append(duplicate)
        with self.assertRaises(PursuitError):
            evaluate(self.p, AS_OF)

    def test_duplicate_json_key_fails(self) -> None:
        with self.assertRaises(PursuitError):
            strict_json_loads('{"x":1,"x":2}')

    def test_nonfinite_json_fails(self) -> None:
        with self.assertRaises(PursuitError):
            strict_json_loads('{"x":NaN}')

    def test_expired_is_literal(self) -> None:
        p = officialize(self.p)
        self.assertEqual(evaluate(p, "2026-10-16T21:00:00Z")["disposition"], "EXPIRED")

    def test_order_invariant_sources_and_gates(self) -> None:
        a = evaluate(self.p, AS_OF)
        self.p["sources"].reverse()
        self.p["gates"].reverse()
        b = evaluate(self.p, AS_OF)
        self.assertEqual(a["disposition"], b["disposition"])
        self.assertEqual(a["source_posture"], b["source_posture"])
        self.assertEqual(a["qualification"], b["qualification"])

    def test_verifier_detects_tamper(self) -> None:
        out = evaluate(self.p, AS_OF)
        self.assertTrue(verify(self.p, AS_OF, out))
        out["disposition"] = "PRIME_READY_FOR_OWNER_SUBMISSION_REVIEW"
        self.assertFalse(verify(self.p, AS_OF, out))

    def test_required_gate_universe_stable(self) -> None:
        self.assertEqual(len(REQUIRED_GATES), 10)

    def test_budget_exact_arithmetic(self) -> None:
        out = validate_budget(
            {
                "workstreams": {
                    "discovery_inventory": "12000.00",
                    "risk_controls": "18000.00",
                    "policy_training": "20000.00",
                },
                "milestones": [
                    {"milestone_id": "discovery", "amount": "12000"},
                    {"milestone_id": "draft", "amount": "18000"},
                    {"milestone_id": "final", "amount": "20000"},
                ],
                "pricing_structure_known": True,
                "buyer_max_total": "60000",
                "owner_approved": False,
            }
        )
        self.assertEqual(out["total_cents"], 5_000_000)
        self.assertTrue(out["math_valid"])

    def test_budget_milestone_mismatch_fails(self) -> None:
        with self.assertRaises(BudgetError):
            validate_budget(
                {
                    "workstreams": {"a": "10", "b": "20"},
                    "milestones": [{"milestone_id": "m", "amount": "29"}],
                    "pricing_structure_known": True,
                    "buyer_max_total": None,
                    "owner_approved": False,
                }
            )

    def test_budget_ceiling_fails(self) -> None:
        with self.assertRaises(BudgetError):
            validate_budget(
                {
                    "workstreams": {"a": "60000.01"},
                    "milestones": [{"milestone_id": "m", "amount": "60000.01"}],
                    "pricing_structure_known": True,
                    "buyer_max_total": "60000",
                    "owner_approved": False,
                }
            )

    def test_budget_unknown_pricing_cannot_be_owner_approved(self) -> None:
        with self.assertRaises(BudgetError):
            validate_budget(
                {
                    "workstreams": {"a": "1"},
                    "milestones": [{"milestone_id": "m", "amount": "1"}],
                    "pricing_structure_known": False,
                    "buyer_max_total": None,
                    "owner_approved": True,
                }
            )


if __name__ == "__main__":
    unittest.main()
