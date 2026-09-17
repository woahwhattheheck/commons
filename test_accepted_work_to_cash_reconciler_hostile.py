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

    def test_provider_confirmation_must_be_independently_bound(self):
        events = _base_events("self-confirm") + [
            _event("self-confirm-a", "ACCEPTED", "2026-09-17T03:00:00Z", "BUYER_MESSAGE"),
            _event("self-confirm-i", "INVOICE_ISSUED", "2026-09-17T04:00:00Z", "BUYER_MESSAGE", amount=500_000),
            _event("self-confirm-p", "PAYMENT_RECEIVED", "2026-09-17T05:00:00Z", "PROVIDER_RECEIPT", amount=500_000),
        ]
        payment = events[-1]
        confirmation = {
            "opportunity_id": "self-confirm",
            "payment_event_id": "self-confirm-p",
            "observed_at": "2026-09-17T06:00:00Z",
            "provider_ref": payment["ref"],
            "provider_sha256": payment["sha256"],
        }
        with self.assertRaisesRegex(ReconcilerError, "independently bound"):
            compile_packet(
                _document(
                    [_opportunity("self-confirm", events)],
                    confirmations=[confirmation],
                )
            )

    def test_distinct_provider_confirmation_still_closes_paid(self):
        events = _base_events("separate-confirm") + [
            _event("separate-confirm-a", "ACCEPTED", "2026-09-17T03:00:00Z", "BUYER_MESSAGE"),
            _event("separate-confirm-i", "INVOICE_ISSUED", "2026-09-17T04:00:00Z", "BUYER_MESSAGE", amount=500_000),
            _event("separate-confirm-p", "PAYMENT_RECEIVED", "2026-09-17T05:00:00Z", "PROVIDER_RECEIPT", amount=500_000),
        ]
        confirmation = {
            "opportunity_id": "separate-confirm",
            "payment_event_id": "separate-confirm-p",
            "observed_at": "2026-09-17T06:00:00Z",
            "provider_ref": "provider://separate/receipt",
            "provider_sha256": _sha("independent-provider-receipt"),
        }
        item = compile_packet(
            _document(
                [_opportunity("separate-confirm", events)],
                confirmations=[confirmation],
            )
        )["items"][0]
        self.assertEqual(item["terminal_action"], "DONE_PAID")


if __name__ == "__main__":
    unittest.main()
