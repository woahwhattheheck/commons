import hashlib
import importlib
import unittest
from datetime import datetime, timezone

MODULE = importlib.import_module("revenue.outbound_delivery_reconciliation.reconcile")
FIXED = datetime(2026, 9, 14, 13, 0, tzinfo=timezone.utc)


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def original():
    return {
        "schema": "outbound-delivery-original/v1",
        "provider_message_id": "msg-1",
        "recipient": "billing@example.com",
        "buyer_scope": "example.com",
        "opportunity_id": "cold-v1",
        "sent_at": "2026-09-14T12:00:00Z",
        "evidence_sha256": digest("sent"),
    }


def failure(**updates):
    row = {
        "schema": "outbound-delivery-provider-event/v1",
        "event_id": "dsn-1",
        "provider_message_id": "msg-1",
        "recipient": "billing@example.com",
        "buyer_scope": "example.com",
        "opportunity_id": "cold-v1",
        "observed_at": "2026-09-14T12:05:00Z",
        "event_kind": "PERMANENT_FAILURE",
        "reason_code": "NO_SUCH_USER",
        "evidence_sha256": digest("dsn"),
    }
    row.update(updates)
    return row


class DnrBoundaryTests(unittest.TestCase):
    def compile(self, row):
        return MODULE._compile_at(original(), [row], at=FIXED)

    def test_cross_recipient_failure_cannot_dnr_original_route(self):
        report = self.compile(failure(recipient="other@example.com"))
        self.assertEqual("HOLD_CONFLICTING_PROVIDER_EVIDENCE", report["classification"])
        self.assertIn("CROSS_RECIPIENT_EVENT:dsn-1", report["hold_reasons"])
        self.assertFalse(report["failed_route_dnr"])
        self.assertEqual([], report["failure_reason_codes"])

    def test_future_failure_cannot_dnr_original_route(self):
        report = self.compile(failure(observed_at="2026-09-14T14:00:00Z"))
        self.assertEqual("HOLD_CONFLICTING_PROVIDER_EVIDENCE", report["classification"])
        self.assertIn("EVENT_FROM_FUTURE:dsn-1", report["hold_reasons"])
        self.assertFalse(report["failed_route_dnr"])
        self.assertEqual([], report["failure_reason_codes"])


if __name__ == "__main__":
    unittest.main()
