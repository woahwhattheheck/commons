from __future__ import annotations

import copy
import unittest
from datetime import datetime, timezone

from revenue.pilot_renewal_expansion_gate.gate import (
    AUTHORITY, GateError, TRUTH_CEILING, canonical_json, compile_packet, normalize,
    strict_loads, verify_current,
)

NOW = datetime(2026, 9, 17, 18, 0, tzinfo=timezone.utc)
H = "a" * 64


def sample():
    return {
        "schema": "pilot-renewal-expansion/v1",
        "engagement": {"id": "eng-1", "organization_id": "org-1", "label": "Paid pilot", "generation": 2},
        "sources": [
            {"id": "s-1", "locator": "repo://receipts/commercial.json", "sha256": H, "observed_at": "2026-09-17T14:00:00Z"},
            {"id": "s-2", "locator": "https://provider.example/receipt", "sha256": "b" * 64, "observed_at": "2026-09-17T14:05:00Z"},
        ],
        "evidence": [
            {"id": "e-base", "kind": "BASELINE_ACCEPTANCE", "subject_id": "baseline-2", "source_id": "s-1", "status": "VERIFIED", "observed_at": "2026-09-17T14:00:00Z", "valid_through": "2026-10-01T00:00:00Z", "summary": "Buyer acceptance receipt"},
            {"id": "e-co", "kind": "CHANGE_ORDER_APPROVAL", "subject_id": "co-1", "source_id": "s-1", "status": "VERIFIED", "observed_at": "2026-09-17T14:01:00Z", "summary": "Approved change"},
            {"id": "e-ms", "kind": "MILESTONE_ACCEPTANCE", "subject_id": "ms-1", "source_id": "s-1", "status": "VERIFIED", "observed_at": "2026-09-17T14:02:00Z", "summary": "Milestone accepted"},
            {"id": "e-pay", "kind": "PAYMENT_SETTLED", "subject_id": "inv-1", "source_id": "s-2", "status": "VERIFIED", "observed_at": "2026-09-17T14:06:00Z", "summary": "Provider settlement"},
            {"id": "e-find", "kind": "SUPPORT_FINDING", "subject_id": "finding-1", "source_id": "s-1", "status": "VERIFIED", "observed_at": "2026-09-17T14:04:00Z", "summary": "Observed support request"},
            {"id": "e-gap", "kind": "GAP_STATUS", "subject_id": "gap-1", "source_id": "s-1", "status": "VERIFIED", "observed_at": "2026-09-17T14:04:00Z", "summary": "Gap closed"},
            {"id": "e-window", "kind": "RENEWAL_WINDOW", "subject_id": "eng-1", "source_id": "s-1", "status": "VERIFIED", "observed_at": "2026-09-17T14:04:00Z", "valid_through": "2026-09-30T23:59:59Z", "summary": "Contract renewal window"},
        ],
        "commercial_baseline": {"id": "baseline-2", "generation": 2, "acceptance_evidence_id": "e-base"},
        "change_orders": [{"id": "co-1", "generation": 1, "state": "APPROVED", "approval_evidence_id": "e-co"}],
        "milestones": [{"id": "ms-1", "required": True, "state": "ACCEPTED", "acceptance_evidence_id": "e-ms"}],
        "payments": [{"id": "inv-1", "required_for_renewal": True, "state": "SETTLED", "settlement_evidence_id": "e-pay"}],
        "support_findings": [{"id": "finding-1", "category": "workflow", "state": "OBSERVED", "summary": "Potential adjacent workflow", "evidence_id": "e-find"}],
        "gaps": [{"id": "gap-1", "kind": "SECURITY", "blocking": True, "state": "CLOSED", "evidence_id": "e-gap"}],
        "renewal_window": {"open_at": "2026-09-17T00:00:00Z", "close_at": "2026-09-30T23:59:59Z", "evidence_id": "e-window"},
        "expansion_hypotheses": [{"id": "x-1", "statement": "Extend evidence automation to a second workflow", "state": TRUTH_CEILING, "supporting_evidence_ids": ["e-find"]}],
        "communication": {"muse_key": "renewal-eng-1", "organization_id": "org-1", "route_id": "buyer-email", "send_state": "NOT_AUTHORIZED"},
    }


class GateTests(unittest.TestCase):
    def compile(self, doc=None, now=NOW):
        return compile_packet(sample() if doc is None else doc, now)

    def test_ready(self):
        _, packet, receipt = self.compile()
        self.assertEqual(packet["decision"], "READY_FOR_RENEWAL_REVIEW")
        self.assertEqual(packet["authority"], AUTHORITY)
        self.assertFalse(any(packet["authority"].values()))
        self.assertEqual(receipt["decision"], packet["decision"])

    def test_delivered_is_not_accepted(self):
        d = sample(); d["milestones"][0]["state"] = "DELIVERED"
        self.assertEqual(self.compile(d)[1]["decision"], "HOLD_ACCEPTANCE")

    def test_missing_baseline_acceptance_holds(self):
        d = sample(); d["evidence"][0]["status"] = "MISSING"
        self.assertEqual(self.compile(d)[1]["decision"], "HOLD_ACCEPTANCE")

    def test_wrong_baseline_subject_holds(self):
        d = sample(); d["evidence"][0]["subject_id"] = "other"
        self.assertEqual(self.compile(d)[1]["decision"], "HOLD_ACCEPTANCE")

    def test_proposed_change_not_treated_approved(self):
        d = sample(); d["change_orders"][0]["state"] = "PROPOSED"
        packet = self.compile(d)[1]
        self.assertEqual(packet["decision"], "READY_FOR_RENEWAL_REVIEW")
        self.assertEqual(packet["approved_change_orders"], [])

    def test_approved_change_requires_evidence(self):
        d = sample(); d["evidence"][1]["status"] = "PROVIDED_UNVERIFIED"
        self.assertEqual(self.compile(d)[1]["decision"], "HOLD_ACCEPTANCE")

    def test_invoice_is_not_payment(self):
        d = sample(); d["payments"][0]["state"] = "INVOICED"
        self.assertEqual(self.compile(d)[1]["decision"], "HOLD_PAYMENT")

    def test_payment_link_is_not_payment(self):
        d = sample(); d["payments"][0]["state"] = "PAYMENT_LINK_SENT"
        self.assertEqual(self.compile(d)[1]["decision"], "HOLD_PAYMENT")

    def test_settled_requires_provider_evidence(self):
        d = sample(); d["evidence"][3]["status"] = "MISSING"
        self.assertEqual(self.compile(d)[1]["decision"], "HOLD_PAYMENT")

    def test_before_window_holds(self):
        early = datetime(2026, 9, 16, 23, 59, tzinfo=timezone.utc)
        self.assertEqual(self.compile(now=early)[1]["decision"], "HOLD_ACCEPTANCE")

    def test_after_window_holds(self):
        late = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(self.compile(now=late)[1]["decision"], "HOLD_EVIDENCE")

    def test_window_only_mismatch_holds_window(self):
        d = sample(); d["renewal_window"]["open_at"] = "2026-09-18T00:00:00Z"
        self.assertEqual(self.compile(d)[1]["decision"], "HOLD_WINDOW")

    def test_blocking_open_gap_holds(self):
        d = sample(); d["gaps"][0]["state"] = "OPEN"
        self.assertEqual(self.compile(d)[1]["decision"], "HOLD_EVIDENCE")

    def test_nonblocking_open_gap_can_review(self):
        d = sample(); d["gaps"][0]["state"] = "OPEN"; d["gaps"][0]["blocking"] = False
        self.assertEqual(self.compile(d)[1]["decision"], "READY_FOR_RENEWAL_REVIEW")

    def test_expansion_cannot_claim_acceptance(self):
        d = sample(); d["expansion_hypotheses"][0]["state"] = "ACCEPTED"
        with self.assertRaises(GateError): normalize(d)

    def test_external_send_cannot_be_enabled(self):
        d = sample(); d["communication"]["send_state"] = "AUTHORIZED"
        with self.assertRaises(GateError): normalize(d)

    def test_organization_route_bound(self):
        d = sample(); d["communication"]["organization_id"] = "org-2"
        with self.assertRaises(GateError): normalize(d)

    def test_verified_dnr_is_terminal(self):
        d = sample(); d["evidence"].append({"id": "e-dnr", "kind": "DNR", "subject_id": "eng-1", "source_id": "s-1", "status": "VERIFIED", "observed_at": "2026-09-17T15:00:00Z", "summary": "Buyer declined renewal"})
        self.assertEqual(self.compile(d)[1]["decision"], "DNR")

    def test_unverified_dnr_not_terminal(self):
        d = sample(); d["evidence"].append({"id": "e-dnr", "kind": "DNR", "subject_id": "eng-1", "source_id": "s-1", "status": "PROVIDED_UNVERIFIED", "observed_at": "2026-09-17T15:00:00Z", "summary": "Rumor"})
        self.assertEqual(self.compile(d)[1]["decision"], "READY_FOR_RENEWAL_REVIEW")

    def test_future_evidence_holds(self):
        d = sample(); d["evidence"][4]["observed_at"] = "2026-09-18T00:00:00Z"
        self.assertEqual(self.compile(d)[1]["decision"], "HOLD_EVIDENCE")

    def test_expired_acceptance_holds(self):
        d = sample(); d["evidence"][0]["valid_through"] = "2026-09-17T17:00:00Z"
        self.assertEqual(self.compile(d)[1]["decision"], "HOLD_ACCEPTANCE")

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(GateError): strict_loads(b'{"schema":"a","schema":"b"}')

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(GateError): strict_loads(b'{"x":NaN}')

    def test_bool_int_alias_rejected(self):
        d = sample(); d["engagement"]["generation"] = True
        with self.assertRaises(GateError): normalize(d)

    def test_unknown_field_rejected(self):
        d = sample(); d["engagement"]["surprise"] = "x"
        with self.assertRaises(GateError): normalize(d)

    def test_duplicate_evidence_ids_rejected(self):
        d = sample(); d["evidence"].append(copy.deepcopy(d["evidence"][0]))
        with self.assertRaises(GateError): normalize(d)

    def test_input_order_deterministic(self):
        d = sample(); d["evidence"] = list(reversed(d["evidence"])); d["sources"] = list(reversed(d["sources"]))
        n1, p1, _ = self.compile(sample())
        n2, p2, _ = self.compile(d)
        self.assertEqual(canonical_json(n1), canonical_json(n2))
        self.assertEqual(canonical_json(p1), canonical_json(p2))

    def test_receipt_tamper_rejected(self):
        raw = sample(); _, packet, receipt = self.compile(raw)
        packet = copy.deepcopy(packet); packet["decision"] = "DNR"
        with self.assertRaises(GateError): verify_current(raw, packet, receipt, NOW)

    def test_input_reseal_tamper_rejected(self):
        raw = sample(); _, packet, receipt = self.compile(raw)
        raw["engagement"]["label"] = "Changed"
        with self.assertRaises(GateError): verify_current(raw, packet, receipt, NOW)

    def test_future_receipt_rejected(self):
        raw = sample(); _, packet, receipt = self.compile(raw, datetime(2026, 9, 19, tzinfo=timezone.utc))
        with self.assertRaises(GateError): verify_current(raw, packet, receipt, NOW)

    def test_current_verifier_detects_later_window_change(self):
        raw = sample(); _, packet, receipt = self.compile(raw)
        result = verify_current(raw, packet, receipt, datetime(2026, 9, 18, 18, 0, tzinfo=timezone.utc))
        self.assertTrue(result["current_valid"])
        result2 = verify_current(raw, packet, receipt, datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc))
        self.assertFalse(result2["current_valid"])
        self.assertNotEqual(result2["current_decision"], "READY_FOR_RENEWAL_REVIEW")

    def test_future_source_observation_invalidates_bound_evidence(self):
        d = sample(); d["sources"][0]["observed_at"] = "2026-09-18T00:00:00Z"
        self.assertEqual(self.compile(d)[1]["decision"], "HOLD_ACCEPTANCE")

    def test_resealed_valid_until_extension_rejected(self):
        from revenue.pilot_renewal_expansion_gate.gate import sha256
        raw = sample(); _, packet, receipt = self.compile(raw)
        receipt = copy.deepcopy(receipt)
        receipt["valid_until"] = "2027-09-30T23:59:59Z"
        core = {k: receipt[k] for k in receipt if k != "receipt_sha256"}
        receipt["receipt_sha256"] = sha256(canonical_json(core))
        with self.assertRaises(GateError): verify_current(raw, packet, receipt, NOW)

    def test_resealed_packet_semantic_rewrite_rejected(self):
        from revenue.pilot_renewal_expansion_gate.gate import sha256
        raw = sample(); _, packet, receipt = self.compile(raw)
        packet = copy.deepcopy(packet); packet["decision"] = "DNR"
        receipt = copy.deepcopy(receipt); receipt["decision"] = "DNR"
        receipt["packet_sha256"] = sha256(canonical_json(packet))
        core = {k: receipt[k] for k in receipt if k != "receipt_sha256"}
        receipt["receipt_sha256"] = sha256(canonical_json(core))
        with self.assertRaises(GateError): verify_current(raw, packet, receipt, NOW)


if __name__ == "__main__":
    unittest.main()
