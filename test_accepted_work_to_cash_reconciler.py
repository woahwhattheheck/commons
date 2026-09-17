from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from revenue.accepted_work_to_cash_reconciler.engine import (
    ReconcilerError,
    compile_bundle,
    compile_packet,
    load_json_strict,
    verify_bundle,
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _event(eid: str, kind: str, at: str, source_class: str, *, amount: int | None = None) -> dict:
    return {
        "id": eid,
        "kind": kind,
        "observed_at": at,
        "source_class": source_class,
        "ref": f"https://example.invalid/evidence/{eid}",
        "sha256": _sha(f"evidence:{eid}"),
        "amount_cents": amount,
    }


def _base_events(oid: str, *, claim_amount: int = 500_000) -> list[dict]:
    return [
        _event(f"{oid}-q", "QUALIFIED", "2026-09-17T01:00:00Z", "GITHUB"),
        _event(
            f"{oid}-claim",
            "CLAIM_SUBMITTED",
            "2026-09-17T02:00:00Z",
            "GITHUB",
            amount=claim_amount,
        ),
    ]


def _opportunity(oid: str, events: list[dict], *, reference_amount: int | None = 500_000, lane: str = "CONTRACT") -> dict:
    return {
        "id": oid,
        "title": f"Opportunity {oid}",
        "lane": lane,
        "currency": "USD",
        "reference_amount_cents": reference_amount,
        "events": events,
    }


def _document(opportunities: list[dict], *, routes: list[dict] | None = None, confirmations: list[dict] | None = None) -> dict:
    return {
        "schema": "TJL_ACCEPTED_WORK_TO_CASH_V1",
        "funnel_input": {
            "schema": "TJL_REVENUE_FUNNEL_V1",
            "evaluation_at": "2026-09-17T07:00:00Z",
            "micro_batch_threshold_cents": 10_000,
            "opportunities": opportunities,
        },
        "routes": routes or [],
        "payment_confirmations": confirmations or [],
    }


def _route(oid: str, *, recipient: str = "owner@example.test", purpose: str = "settlement follow-up", at: str = "2026-09-17T06:30:00Z") -> dict:
    return {
        "opportunity_id": oid,
        "recipient": recipient,
        "purpose": purpose,
        "observed_at": at,
        "source_class": "PROVIDER_DIRECTORY",
        "ref": f"https://example.invalid/routes/{oid}",
        "sha256": _sha(f"route:{oid}"),
    }


def _confirmation(oid: str, payment_event_id: str, *, at: str = "2026-09-17T06:59:00Z") -> dict:
    return {
        "opportunity_id": oid,
        "payment_event_id": payment_event_id,
        "observed_at": at,
        "provider_ref": f"provider://receipt/{oid}/{payment_event_id}",
        "provider_sha256": _sha(f"provider:{oid}:{payment_event_id}"),
    }


class AcceptedWorkToCashTests(unittest.TestCase):
    def test_merged_only_is_not_external_acceptance(self):
        events = _base_events("merged") + [_event("merged-m", "MERGED", "2026-09-17T03:00:00Z", "GITHUB")]
        item = compile_packet(_document([_opportunity("merged", events)]))["items"][0]
        self.assertEqual(item["stage"], "ACCEPTED_OR_MERGED")
        self.assertEqual(item["acceptance_basis"], "MERGED_WORK_ONLY")
        self.assertEqual(item["terminal_action"], "ACCEPTANCE_EVIDENCE_REQUIRED")

    def test_buyer_acceptance_reaches_internal_invoice_prep_only(self):
        events = _base_events("accepted") + [_event("accepted-a", "ACCEPTED", "2026-09-17T03:00:00Z", "BUYER_MESSAGE")]
        packet = compile_packet(_document([_opportunity("accepted", events)]))
        item = packet["items"][0]
        self.assertEqual(item["acceptance_basis"], "EXTERNAL_ACCEPTANCE_EVIDENCE")
        self.assertEqual(item["terminal_action"], "OWNER_INVOICE_PREPARATION_REVIEW")
        self.assertFalse(packet["authority"]["invoice_creation"])

    def test_unpaid_invoice_with_route_stops_at_muse(self):
        events = _base_events("invoice") + [
            _event("invoice-a", "ACCEPTED", "2026-09-17T03:00:00Z", "BUYER_MESSAGE"),
            _event("invoice-i", "INVOICE_ISSUED", "2026-09-17T04:00:00Z", "BUYER_MESSAGE", amount=500_000),
        ]
        item = compile_packet(_document([_opportunity("invoice", events)], routes=[_route("invoice")]))["items"][0]
        self.assertEqual(item["stage"], "INVOICED_OR_AWARDED")
        self.assertEqual(item["terminal_action"], "MUSE_REQUIRED")
        self.assertEqual(item["muse_packet"]["recipient"], "owner@example.test")
        self.assertEqual(item["muse_packet"]["authority"], "REQUEST_ARBITRATION_ONLY_NOT_SEND_AUTHORITY")

    def test_historical_muse_clear_does_not_become_send_authority(self):
        events = _base_events("muse") + [
            _event("muse-a", "ACCEPTED", "2026-09-17T03:00:00Z", "BUYER_MESSAGE"),
            _event("muse-mc", "MUSE_CLEAR", "2026-09-17T03:30:00Z", "SLACK"),
            _event("muse-i", "INVOICE_ISSUED", "2026-09-17T04:00:00Z", "BUYER_MESSAGE", amount=500_000),
        ]
        item = compile_packet(_document([_opportunity("muse", events)], routes=[_route("muse")]))["items"][0]
        self.assertEqual(item["terminal_action"], "MUSE_REQUIRED")

    def test_prior_outbound_waits_instead_of_repeating_contact(self):
        events = _base_events("sent") + [
            _event("sent-a", "ACCEPTED", "2026-09-17T03:00:00Z", "BUYER_MESSAGE"),
            _event("sent-i", "INVOICE_ISSUED", "2026-09-17T04:00:00Z", "BUYER_MESSAGE", amount=500_000),
            _event("sent-o", "OUTBOUND_SENT", "2026-09-17T05:00:00Z", "PROVIDER_RECEIPT"),
        ]
        item = compile_packet(_document([_opportunity("sent", events)], routes=[_route("sent")]))["items"][0]
        self.assertEqual(item["contact_state"], "WAIT_EXTERNAL")
        self.assertEqual(item["terminal_action"], "WAIT_EXTERNAL")

    def test_later_inbound_becomes_review_not_send(self):
        events = _base_events("reply") + [
            _event("reply-a", "ACCEPTED", "2026-09-17T03:00:00Z", "BUYER_MESSAGE"),
            _event("reply-i", "INVOICE_ISSUED", "2026-09-17T04:00:00Z", "BUYER_MESSAGE", amount=500_000),
            _event("reply-o", "OUTBOUND_SENT", "2026-09-17T05:00:00Z", "PROVIDER_RECEIPT"),
            _event("reply-r", "INBOUND_RECEIVED", "2026-09-17T06:00:00Z", "BUYER_MESSAGE"),
        ]
        item = compile_packet(_document([_opportunity("reply", events)], routes=[_route("reply")]))["items"][0]
        self.assertEqual(item["contact_state"], "NEW_INBOUND")
        self.assertEqual(item["terminal_action"], "INBOUND_REVIEW")

    def test_dnr_is_inbound_only(self):
        events = _base_events("dnr") + [
            _event("dnr-a", "ACCEPTED", "2026-09-17T03:00:00Z", "BUYER_MESSAGE"),
            _event("dnr-i", "INVOICE_ISSUED", "2026-09-17T04:00:00Z", "BUYER_MESSAGE", amount=500_000),
            _event("dnr-d", "DNR", "2026-09-17T05:00:00Z", "SLACK"),
        ]
        item = compile_packet(_document([_opportunity("dnr", events)], routes=[_route("dnr")]))["items"][0]
        self.assertEqual(item["contact_state"], "HARD_DNR")
        self.assertEqual(item["terminal_action"], "INBOUND_ONLY")

    def test_collision_holds(self):
        events = _base_events("collision") + [
            _event("collision-a", "ACCEPTED", "2026-09-17T03:00:00Z", "BUYER_MESSAGE"),
            _event("collision-i", "INVOICE_ISSUED", "2026-09-17T04:00:00Z", "BUYER_MESSAGE", amount=500_000),
            _event("collision-c", "COLLISION_HOLD", "2026-09-17T05:00:00Z", "SLACK"),
        ]
        item = compile_packet(_document([_opportunity("collision", events)], routes=[_route("collision")]))["items"][0]
        self.assertEqual(item["terminal_action"], "HOLD_COLLISION")

    def test_missing_route_is_explicit(self):
        events = _base_events("route") + [
            _event("route-a", "ACCEPTED", "2026-09-17T03:00:00Z", "BUYER_MESSAGE"),
            _event("route-i", "INVOICE_ISSUED", "2026-09-17T04:00:00Z", "BUYER_MESSAGE", amount=500_000),
        ]
        item = compile_packet(_document([_opportunity("route", events)]))["items"][0]
        self.assertEqual(item["terminal_action"], "ROUTE_EVIDENCE_REQUIRED")

    def test_paid_requires_provider_authentication_not_retained_assertion(self):
        events = _base_events("paid") + [
            _event("paid-a", "ACCEPTED", "2026-09-17T03:00:00Z", "BUYER_MESSAGE"),
            _event("paid-i", "INVOICE_ISSUED", "2026-09-17T04:00:00Z", "BUYER_MESSAGE", amount=500_000),
            _event("paid-p", "PAYMENT_RECEIVED", "2026-09-17T05:00:00Z", "PROVIDER_RECEIPT", amount=500_000),
        ]
        packet = compile_packet(_document([_opportunity("paid", events)]))
        item = packet["items"][0]
        self.assertEqual(item["stage"], "PAID")
        self.assertEqual(item["terminal_action"], "VERIFY_PROVIDER_CASH")
        self.assertEqual(item["cash_state"], "RETAINED_PAYMENT_EVENTS_UNCONFIRMED")
        self.assertFalse(packet["summary"]["provider_authenticated_payment_evidence_available"])
        self.assertTrue(packet["summary"]["terminal_paid_requires_provider_authenticated_evidence"])

    def test_retained_confirmation_never_closes_paid(self):
        events = _base_events("paid") + [
            _event("paid-a", "ACCEPTED", "2026-09-17T03:00:00Z", "BUYER_MESSAGE"),
            _event("paid-i", "INVOICE_ISSUED", "2026-09-17T04:00:00Z", "BUYER_MESSAGE", amount=500_000),
            _event("paid-p", "PAYMENT_RECEIVED", "2026-09-17T05:00:00Z", "PROVIDER_RECEIPT", amount=500_000),
        ]
        item = compile_packet(_document([_opportunity("paid", events)], confirmations=[_confirmation("paid", "paid-p")]))["items"][0]
        self.assertEqual(item["terminal_action"], "VERIFY_PROVIDER_CASH")
        self.assertEqual(item["cash_state"], "RETAINED_CONFIRMATIONS_COMPLETE_UNAUTHENTICATED")

    def test_confirmation_must_bind_payment_event(self):
        events = _base_events("paid") + [
            _event("paid-a", "ACCEPTED", "2026-09-17T03:00:00Z", "BUYER_MESSAGE"),
            _event("paid-i", "INVOICE_ISSUED", "2026-09-17T04:00:00Z", "BUYER_MESSAGE", amount=500_000),
            _event("paid-p", "PAYMENT_RECEIVED", "2026-09-17T05:00:00Z", "PROVIDER_RECEIPT", amount=500_000),
        ]
        with self.assertRaisesRegex(ReconcilerError, "does not bind"):
            compile_packet(_document([_opportunity("paid", events)], confirmations=[_confirmation("paid", "missing")]))

    def test_confirmation_cannot_predate_payment(self):
        events = _base_events("paid") + [
            _event("paid-a", "ACCEPTED", "2026-09-17T03:00:00Z", "BUYER_MESSAGE"),
            _event("paid-i", "INVOICE_ISSUED", "2026-09-17T04:00:00Z", "BUYER_MESSAGE", amount=500_000),
            _event("paid-p", "PAYMENT_RECEIVED", "2026-09-17T05:00:00Z", "PROVIDER_RECEIPT", amount=500_000),
        ]
        with self.assertRaisesRegex(ReconcilerError, "predates"):
            compile_packet(_document([_opportunity("paid", events)], confirmations=[_confirmation("paid", "paid-p", at="2026-09-17T04:59:59Z")]))

    def test_unknown_route_and_duplicate_route_fail_closed(self):
        qual = _opportunity("q", [_event("q-q", "QUALIFIED", "2026-09-17T01:00:00Z", "GITHUB")])
        with self.assertRaisesRegex(ReconcilerError, "unknown opportunity"):
            compile_packet(_document([qual], routes=[_route("other")]))
        with self.assertRaisesRegex(ReconcilerError, "duplicate route"):
            compile_packet(_document([qual], routes=[_route("q"), _route("q")]))

    def test_queue_is_realizability_first_not_amount_first(self):
        near_events = _base_events("small", claim_amount=100) + [
            _event("small-a", "ACCEPTED", "2026-09-17T03:00:00Z", "BUYER_MESSAGE"),
            _event("small-i", "INVOICE_ISSUED", "2026-09-17T04:00:00Z", "BUYER_MESSAGE", amount=100),
        ]
        far_events = [_event("huge-q", "QUALIFIED", "2026-09-17T01:00:00Z", "GITHUB")]
        packet = compile_packet(_document([
            _opportunity("huge-far", far_events, reference_amount=100_000_000),
            _opportunity("small-near", near_events, reference_amount=100),
        ], routes=[_route("huge-far"), _route("small-near")]))
        self.assertEqual(packet["open_queue"], ["small-near", "huge-far"])
        self.assertFalse(packet["summary"]["queue_uses_headline_amount"])

    def test_bundle_verifier_recompiles_semantics(self):
        events = _base_events("merged") + [_event("merged-m", "MERGED", "2026-09-17T03:00:00Z", "GITHUB")]
        bundle = compile_bundle(_document([_opportunity("merged", events)]))
        self.assertTrue(verify_bundle(bundle))
        forged = copy.deepcopy(bundle)
        forged["packet"]["items"][0]["terminal_action"] = "DONE_PAID"
        self.assertFalse(verify_bundle(forged))

    def test_upstream_invalid_chronology_fails_closed(self):
        events = [
            _event("bad-claim", "CLAIM_SUBMITTED", "2026-09-17T01:00:00Z", "GITHUB", amount=500_000),
            _event("bad-q", "QUALIFIED", "2026-09-17T02:00:00Z", "GITHUB"),
        ]
        with self.assertRaisesRegex(ReconcilerError, "predates qualification"):
            compile_packet(_document([_opportunity("bad", events)]))

    def test_all_authority_bits_are_false(self):
        packet = compile_packet(_document([_opportunity("q", [_event("q-q", "QUALIFIED", "2026-09-17T01:00:00Z", "GITHUB")])]))
        self.assertTrue(all(value is False for value in packet["authority"].values()))

    def test_strict_loader_rejects_duplicate_keys_and_float(self):
        with tempfile.TemporaryDirectory() as td:
            duplicate = Path(td) / "duplicate.json"
            duplicate.write_text('{"a":1,"a":2}', encoding="utf-8")
            with self.assertRaisesRegex(ReconcilerError, "duplicate JSON key"):
                load_json_strict(duplicate)
            floating = Path(td) / "float.json"
            floating.write_text('{"a":1.5}', encoding="utf-8")
            with self.assertRaisesRegex(ReconcilerError, "floating JSON number forbidden"):
                load_json_strict(floating)


if __name__ == "__main__":
    unittest.main()
