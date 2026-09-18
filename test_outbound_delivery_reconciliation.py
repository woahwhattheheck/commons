import copy
import hashlib
import inspect
import unittest
from datetime import datetime, timezone

from revenue.outbound_delivery_reconciliation import reconcile, verify, ReconciliationError


def d(text):
    return hashlib.sha256(text.encode()).hexdigest()


def original(**updates):
    value = {
        "schema": "outbound-delivery-original/v1",
        "provider_message_id": "msg-1",
        "recipient": "billing@example.com",
        "buyer_scope": "example.com",
        "opportunity_id": "cold-v1",
        "sent_at": "2026-09-14T12:00:00Z",
        "evidence_sha256": d("sent"),
    }
    value.update(updates)
    return value


def event(event_id="dsn-1", **updates):
    value = {
        "schema": "outbound-delivery-provider-event/v1",
        "event_id": event_id,
        "provider_message_id": "msg-1",
        "recipient": "billing@example.com",
        "buyer_scope": "example.com",
        "opportunity_id": "cold-v1",
        "observed_at": "2026-09-14T12:05:00Z",
        "event_kind": "PERMANENT_FAILURE",
        "reason_code": "NO_SUCH_USER",
        "evidence_sha256": d(event_id),
    }
    value.update(updates)
    return value


FIXED = datetime(2026, 9, 14, 13, 0, tzinfo=timezone.utc)


class Tests(unittest.TestCase):
    def compile(self, o=None, e=None):
        import importlib
        module = importlib.import_module("revenue.outbound_delivery_reconciliation.reconcile")
        return module._compile_at(o or original(), [] if e is None else e, at=FIXED)

    def test_no_event_pending(self):
        report = self.compile()
        self.assertEqual("SENT_PENDING_PROVIDER_TRUTH", report["classification"])
        self.assertFalse(report["failed_route_dnr"])

    def test_no_such_user_failed_and_dnr(self):
        report = self.compile(e=[event()])
        self.assertEqual("DELIVERY_FAILED", report["classification"])
        self.assertEqual(["NO_SUCH_USER"], report["failure_reason_codes"])
        self.assertTrue(report["failed_route_dnr"])

    def test_every_failure_reason(self):
        reasons = [
            "NO_SUCH_USER", "MAILBOX_FULL", "POLICY_OR_GROUP_RESTRICTION",
            "REMOTE_REJECTION", "UNKNOWN_PERMANENT_FAILURE",
        ]
        for i, reason in enumerate(reasons):
            report = self.compile(e=[event(str(i), reason_code=reason)])
            self.assertEqual("DELIVERY_FAILED", report["classification"])
            self.assertEqual([reason], report["failure_reason_codes"])

    def test_exact_replay_idempotent(self):
        one = event()
        self.assertEqual(
            self.compile(e=[one])["receipt_sha256"],
            self.compile(e=[one, copy.deepcopy(one)])["receipt_sha256"],
        )

    def test_same_id_changed_bytes_holds(self):
        report = self.compile(e=[event(), event(reason_code="MAILBOX_FULL")])
        self.assertEqual("HOLD_CONFLICTING_PROVIDER_EVIDENCE", report["classification"])
        self.assertIn("EVENT_ID_FORK:dsn-1", report["hold_reasons"])

    def test_cross_message_holds(self):
        self.assertIn("CROSS_MESSAGE_EVENT:dsn-1", self.compile(e=[event(provider_message_id="msg-2")])["hold_reasons"])

    def test_cross_recipient_holds(self):
        self.assertIn("CROSS_RECIPIENT_EVENT:dsn-1", self.compile(e=[event(recipient="other@example.com")])["hold_reasons"])

    def test_cross_buyer_holds(self):
        self.assertIn("CROSS_BUYER_EVENT:dsn-1", self.compile(e=[event(buyer_scope="other.example")])["hold_reasons"])

    def test_cross_opportunity_holds(self):
        self.assertIn("CROSS_OPPORTUNITY_EVENT:dsn-1", self.compile(e=[event(opportunity_id="other-op")])["hold_reasons"])

    def test_event_before_send_holds(self):
        self.assertIn("EVENT_BEFORE_SEND:dsn-1", self.compile(e=[event(observed_at="2026-09-14T11:59:59Z")])["hold_reasons"])

    def test_future_event_holds(self):
        self.assertIn("EVENT_FROM_FUTURE:dsn-1", self.compile(e=[event(observed_at="2026-09-14T14:00:00Z")])["hold_reasons"])

    def test_future_original_holds(self):
        self.assertIn("ORIGINAL_SENT_FROM_FUTURE", self.compile(o=original(sent_at="2026-09-14T14:00:00Z"))["hold_reasons"])

    def test_incompatible_terminal_events_hold(self):
        accepted = event("accepted-1", event_kind="PROVIDER_ACCEPTED", reason_code=None, evidence_sha256=d("accepted"))
        report = self.compile(e=[event(), accepted])
        self.assertIn("INCOMPATIBLE_TERMINAL_PROVIDER_EVIDENCE", report["hold_reasons"])
        self.assertEqual("HOLD_CONFLICTING_PROVIDER_EVIDENCE", report["classification"])

    def test_accepted_alone_does_not_assert_delivery(self):
        accepted = event("accepted-1", event_kind="PROVIDER_ACCEPTED", reason_code=None)
        report = self.compile(e=[accepted])
        self.assertEqual("SENT_PENDING_PROVIDER_TRUTH", report["classification"])
        self.assertFalse(report["buyer_rejection_asserted"])
        self.assertFalse(report["buyer_acceptance_asserted"])

    def test_no_authority_flags_are_always_false(self):
        for rows in ([], [event()]):
            report = self.compile(e=rows)
            for key in (
                "alternate_route_authorized", "retry_authorized", "buyer_rejection_asserted",
                "buyer_opt_out_asserted", "buyer_acceptance_asserted", "payment_asserted",
                "cash_asserted", "revenue_asserted",
            ):
                self.assertIs(report[key], False)

    def test_public_reconcile_has_no_clock_argument(self):
        self.assertEqual(["original", "events"], list(inspect.signature(reconcile).parameters))
        with self.assertRaises(TypeError):
            reconcile(original(), [], at=FIXED)

    def test_verify_exact_and_tamper(self):
        report = self.compile(e=[event()])
        self.assertTrue(verify(report, original(), [event()]))
        tampered = copy.deepcopy(report)
        tampered["alternate_route_authorized"] = True
        self.assertFalse(verify(tampered, original(), [event()]))

    def test_verify_input_drift(self):
        report = self.compile(e=[event()])
        self.assertFalse(verify(report, original(), [event(evidence_sha256=d("changed"))]))

    def test_bool_or_non_string_traps(self):
        with self.assertRaises(ReconciliationError):
            self.compile(o=original(provider_message_id=True))
        with self.assertRaises(ReconciliationError):
            self.compile(e=[event(reason_code=1)])

    def test_bad_digest_timestamp_and_controls(self):
        with self.assertRaises(ReconciliationError):
            self.compile(o=original(evidence_sha256="A" * 64))
        with self.assertRaises(ReconciliationError):
            self.compile(e=[event(observed_at="2026-09-14T12:05:00+00:00")])
        with self.assertRaises(ReconciliationError):
            self.compile(e=[event(event_id="bad\nid")])

    def test_order_invariance(self):
        a = event("a", reason_code="MAILBOX_FULL", observed_at="2026-09-14T12:06:00Z")
        b = event("b", reason_code="REMOTE_REJECTION", observed_at="2026-09-14T12:07:00Z")
        self.assertEqual(self.compile(e=[a, b])["receipt_sha256"], self.compile(e=[b, a])["receipt_sha256"])


if __name__ == "__main__":
    unittest.main()
