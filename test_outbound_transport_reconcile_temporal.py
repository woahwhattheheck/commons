from __future__ import annotations

import hashlib
import unittest
from datetime import datetime, timezone

from revenue.outbound_transport_reconcile.reconcile import compile_report, verify_report


NOW = datetime(2026, 9, 13, 12, 55, 0, tzinfo=timezone.utc)
TS = "2026-09-13T12:54:00Z"
CAPTURE = "2026-09-13T12:54:30Z"
H1 = hashlib.sha256(b"recipient-1").hexdigest()
E1 = hashlib.sha256(b"evidence-1").hexdigest()
E2 = hashlib.sha256(b"evidence-2").hexdigest()


def policy(age=3600):
    return {"schema": "outbound-transport-reconcile-policy/v1", "max_snapshot_age_seconds": age}


def gmail(records=None, *, captured_at=CAPTURE):
    return {
        "schema": "gmail-sent-snapshot/v1",
        "snapshot_id": "gmail-temporal-s1",
        "captured_at": captured_at,
        "complete": True,
        "records": records
        if records is not None
        else [
            {
                "message_id": "gm-1",
                "recipient_sha256": H1,
                "sent_at": TS,
                "evidence_sha256": E1,
            }
        ],
    }


def slack(records=None, *, captured_at=CAPTURE):
    return {
        "schema": "slack-send-receipt-snapshot/v1",
        "snapshot_id": "slack-temporal-s1",
        "captured_at": captured_at,
        "complete": True,
        "records": records
        if records is not None
        else [
            {
                "event_id": "sl-1",
                "provider_message_id": "gm-1",
                "recipient_sha256": H1,
                "recorded_at": TS,
                "evidence_sha256": E2,
            }
        ],
    }


class TemporalCoverageTests(unittest.TestCase):
    def test_matched_receipt_before_provider_sent_holds(self):
        s = slack()
        s["records"][0]["recorded_at"] = "2026-09-13T12:53:59Z"
        report = compile_report(gmail(), s, policy(), as_of=NOW)
        self.assertEqual(report["status"], "HOLD")
        self.assertIn("SLACK_RECEIPT_BEFORE_PROVIDER_SENT:sl-1", report["hold_reasons"])

    def test_gmail_event_after_slack_capture_holds_instead_of_false_missing_receipt(self):
        report = compile_report(
            gmail(),
            slack([], captured_at="2026-09-13T12:53:59Z"),
            policy(),
            as_of=NOW,
        )
        self.assertEqual(report["status"], "HOLD")
        self.assertIn("GMAIL_EVENT_OUTSIDE_SLACK_COVERAGE:gm-1", report["hold_reasons"])
        self.assertEqual(report["discrepancies"], [])

    def test_slack_event_after_gmail_capture_holds_instead_of_false_provider_missing(self):
        report = compile_report(
            gmail([], captured_at="2026-09-13T12:53:59Z"),
            slack(),
            policy(),
            as_of=NOW,
        )
        self.assertEqual(report["status"], "HOLD")
        self.assertIn("SLACK_EVENT_OUTSIDE_GMAIL_COVERAGE:sl-1", report["hold_reasons"])
        self.assertEqual(report["discrepancies"], [])

    def test_skewed_snapshots_can_reconcile_when_positive_evidence_is_temporally_sound(self):
        s = slack(captured_at="2026-09-13T12:54:40Z")
        s["records"][0]["recorded_at"] = "2026-09-13T12:54:35Z"
        report = compile_report(
            gmail(captured_at="2026-09-13T12:54:30Z"),
            s,
            policy(),
            as_of=NOW,
        )
        self.assertEqual(report["status"], "LEDGERS_CONSISTENT")
        self.assertEqual(report["common_coverage_through"], "2026-09-13T12:54:30Z")

    def test_common_coverage_is_bound_into_receipt_and_verifier(self):
        report = compile_report(gmail(), slack(), policy(), as_of=NOW)
        self.assertEqual(report["schema"], "outbound-transport-reconcile-report/v2")
        self.assertEqual(report["common_coverage_through"], CAPTURE)
        self.assertTrue(verify_report(report, gmail(), slack(), policy(), as_of=NOW))
        tampered = dict(report)
        tampered["common_coverage_through"] = "2026-09-13T12:54:29Z"
        self.assertFalse(verify_report(tampered, gmail(), slack(), policy(), as_of=NOW))

    def test_in_horizon_provider_absence_remains_reconciliation_required(self):
        report = compile_report(gmail(), slack([]), policy(), as_of=NOW)
        self.assertEqual(report["status"], "RECONCILIATION_REQUIRED")
        self.assertEqual([row["code"] for row in report["discrepancies"]], ["PROVIDER_SENT_NOT_RECORDED"])

    def test_in_horizon_slack_absence_remains_reconciliation_required(self):
        report = compile_report(gmail([]), slack(), policy(), as_of=NOW)
        self.assertEqual(report["status"], "RECONCILIATION_REQUIRED")
        self.assertEqual([row["code"] for row in report["discrepancies"]], ["SLACK_SENT_WITHOUT_PROVIDER_SENT"])


if __name__ == "__main__":
    unittest.main()
