from __future__ import annotations

import unittest

from revenue.accepted_work_to_cash_reconciler.engine import ReconcilerError, compile_packet
from test_accepted_work_to_cash_reconciler import (
    _base_events,
    _document,
    _event,
    _opportunity,
    _route,
    _sha,
)


def _paid_events(oid: str) -> list[dict]:
    return _base_events(oid) + [
        _event(f"{oid}-a", "ACCEPTED", "2026-09-17T03:00:00Z", "BUYER_MESSAGE"),
        _event(
            f"{oid}-i",
            "INVOICE_ISSUED",
            "2026-09-17T04:00:00Z",
            "BUYER_MESSAGE",
            amount=500_000,
        ),
        _event(
            f"{oid}-p",
            "PAYMENT_RECEIVED",
            "2026-09-17T05:00:00Z",
            "PROVIDER_RECEIPT",
            amount=500_000,
        ),
    ]


class AcceptedWorkToCashHostileTests(unittest.TestCase):
    def test_same_second_dnr_beats_inbound_independent_of_event_id(self):
        events = _base_events("tie-dnr") + [
            _event("tie-dnr-a", "ACCEPTED", "2026-09-17T03:00:00Z", "BUYER_MESSAGE"),
            _event("tie-dnr-i", "INVOICE_ISSUED", "2026-09-17T04:00:00Z", "BUYER_MESSAGE", amount=500_000),
            _event("z-inbound", "INBOUND_RECEIVED", "2026-09-17T05:00:00Z", "BUYER_MESSAGE"),
            _event("a-dnr", "DNR", "2026-09-17T05:00:00Z", "SLACK"),
        ]
        item = compile_packet(
            _document([_opportunity("tie-dnr", events)], routes=[_route("tie-dnr")])
        )["items"][0]
        self.assertEqual(item["contact_state"], "HARD_DNR")
        self.assertEqual(item["terminal_action"], "INBOUND_ONLY")

    def test_same_second_inbound_and_outbound_hold_ambiguity(self):
        events = _base_events("tie-io") + [
            _event("tie-io-a", "ACCEPTED", "2026-09-17T03:00:00Z", "BUYER_MESSAGE"),
            _event("tie-io-i", "INVOICE_ISSUED", "2026-09-17T04:00:00Z", "BUYER_MESSAGE", amount=500_000),
            _event("a-inbound", "INBOUND_RECEIVED", "2026-09-17T05:00:00Z", "BUYER_MESSAGE"),
            _event("z-outbound", "OUTBOUND_SENT", "2026-09-17T05:00:00Z", "PROVIDER_RECEIPT"),
        ]
        item = compile_packet(
            _document([_opportunity("tie-io", events)], routes=[_route("tie-io")])
        )["items"][0]
        self.assertEqual(item["contact_state"], "AMBIGUOUS_SAME_TIME_CONTACT")
        self.assertEqual(item["terminal_action"], "HOLD_CONTACT_AMBIGUITY")

    def test_exact_payment_evidence_copy_is_rejected(self):
        events = _paid_events("self-confirm")
        payment = events[-1]
        confirmation = {
            "opportunity_id": "self-confirm",
            "payment_event_id": "self-confirm-p",
            "observed_at": "2026-09-17T06:00:00Z",
            "provider_ref": payment["ref"],
            "provider_sha256": payment["sha256"],
        }
        with self.assertRaisesRegex(ReconcilerError, "copied retained payment evidence"):
            compile_packet(
                _document(
                    [_opportunity("self-confirm", events)],
                    confirmations=[confirmation],
                )
            )

    def test_arbitrary_distinct_ref_and_digest_cannot_close_paid(self):
        events = _paid_events("arbitrary")
        confirmation = {
            "opportunity_id": "arbitrary",
            "payment_event_id": "arbitrary-p",
            "observed_at": "2026-09-17T06:00:00Z",
            "provider_ref": "provider://invented/receipt",
            "provider_sha256": _sha("invented-provider-receipt"),
        }
        packet = compile_packet(
            _document([_opportunity("arbitrary", events)], confirmations=[confirmation])
        )
        item = packet["items"][0]
        self.assertEqual(item["cash_state"], "RETAINED_CONFIRMATIONS_COMPLETE_UNAUTHENTICATED")
        self.assertEqual(item["terminal_action"], "VERIFY_PROVIDER_CASH")
        self.assertFalse(packet["summary"]["provider_authenticated_payment_evidence_available"])

    def test_route_evidence_relabelled_as_cash_confirmation_cannot_close_paid(self):
        events = _paid_events("route-copy")
        route = _route("route-copy")
        confirmation = {
            "opportunity_id": "route-copy",
            "payment_event_id": "route-copy-p",
            "observed_at": "2026-09-17T06:45:00Z",
            "provider_ref": route["ref"],
            "provider_sha256": route["sha256"],
        }
        item = compile_packet(
            _document(
                [_opportunity("route-copy", events)],
                routes=[route],
                confirmations=[confirmation],
            )
        )["items"][0]
        self.assertEqual(item["terminal_action"], "VERIFY_PROVIDER_CASH")
        self.assertEqual(item["cash_state"], "RETAINED_CONFIRMATIONS_COMPLETE_UNAUTHENTICATED")

    def test_different_ref_with_copied_payment_digest_cannot_close_paid(self):
        events = _paid_events("digest-copy")
        payment = events[-1]
        confirmation = {
            "opportunity_id": "digest-copy",
            "payment_event_id": "digest-copy-p",
            "observed_at": "2026-09-17T06:00:00Z",
            "provider_ref": "provider://different/ref",
            "provider_sha256": payment["sha256"],
        }
        item = compile_packet(
            _document(
                [_opportunity("digest-copy", events)],
                confirmations=[confirmation],
            )
        )["items"][0]
        self.assertEqual(item["terminal_action"], "VERIFY_PROVIDER_CASH")
        self.assertEqual(item["cash_state"], "RETAINED_CONFIRMATIONS_COMPLETE_UNAUTHENTICATED")


if __name__ == "__main__":
    unittest.main()
