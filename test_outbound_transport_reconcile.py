from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from revenue.outbound_transport_reconcile.reconcile import (
    ReconcileError,
    canonical_json,
    compile_report,
    strict_json_loads,
    verify_report,
)


NOW = datetime(2026, 9, 13, 12, 55, 0, tzinfo=timezone.utc)
TS = "2026-09-13T12:54:00Z"
CAPTURE = "2026-09-13T12:54:30Z"
H1 = hashlib.sha256(b"recipient-1").hexdigest()
H2 = hashlib.sha256(b"recipient-2").hexdigest()
E1 = hashlib.sha256(b"evidence-1").hexdigest()
E2 = hashlib.sha256(b"evidence-2").hexdigest()


def policy(age=3600):
    return {"schema": "outbound-transport-reconcile-policy/v1", "max_snapshot_age_seconds": age}


def gmail(records=None, *, complete=True, captured_at=CAPTURE):
    return {
        "schema": "gmail-sent-snapshot/v1",
        "snapshot_id": "gmail-s1",
        "captured_at": captured_at,
        "complete": complete,
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


def slack(records=None, *, complete=True, captured_at=CAPTURE):
    return {
        "schema": "slack-send-receipt-snapshot/v1",
        "snapshot_id": "slack-s1",
        "captured_at": captured_at,
        "complete": complete,
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


class ReconcileTests(unittest.TestCase):
    def test_matched_ledgers_consistent(self):
        report = compile_report(gmail(), slack(), policy(), as_of=NOW)
        self.assertEqual(report["status"], "LEDGERS_CONSISTENT")
        self.assertEqual(report["discrepancies"], [])
        self.assertFalse(report["authority"]["resend_authorized"])
        self.assertTrue(verify_report(report, gmail(), slack(), policy(), as_of=NOW))

    def test_provider_sent_missing_slack(self):
        report = compile_report(gmail(), slack([]), policy(), as_of=NOW)
        self.assertEqual(report["status"], "RECONCILIATION_REQUIRED")
        self.assertEqual([r["code"] for r in report["discrepancies"]], ["PROVIDER_SENT_NOT_RECORDED"])

    def test_slack_claim_without_provider(self):
        report = compile_report(gmail([]), slack(), policy(), as_of=NOW)
        self.assertEqual(report["status"], "RECONCILIATION_REQUIRED")
        self.assertEqual([r["code"] for r in report["discrepancies"]], ["SLACK_SENT_WITHOUT_PROVIDER_SENT"])

    def test_unbound_slack_receipt(self):
        rows = slack()["records"]
        rows[0]["provider_message_id"] = None
        report = compile_report(gmail(), slack(rows), policy(), as_of=NOW)
        codes = [r["code"] for r in report["discrepancies"]]
        self.assertEqual(codes, ["PROVIDER_SENT_NOT_RECORDED", "SLACK_RECEIPT_UNBOUND"])

    def test_recipient_conflict(self):
        rows = slack()["records"]
        rows[0]["recipient_sha256"] = H2
        report = compile_report(gmail(), slack(rows), policy(), as_of=NOW)
        self.assertEqual([r["code"] for r in report["discrepancies"]], ["PROVIDER_RECIPIENT_CONFLICT"])

    def test_duplicate_slack_receipt_is_reconciliation(self):
        rows = slack()["records"]
        extra = copy.deepcopy(rows[0])
        extra["event_id"] = "sl-2"
        report = compile_report(gmail(), slack(rows + [extra]), policy(), as_of=NOW)
        codes = [r["code"] for r in report["discrepancies"]]
        self.assertEqual(codes, ["DUPLICATE_OR_CONFLICTING_RECEIPT", "DUPLICATE_OR_CONFLICTING_RECEIPT"])

    def test_exact_stable_id_replay_collapses(self):
        g = gmail()
        g["records"].append(copy.deepcopy(g["records"][0]))
        s = slack()
        s["records"].append(copy.deepcopy(s["records"][0]))
        report = compile_report(g, s, policy(), as_of=NOW)
        self.assertEqual(report["status"], "LEDGERS_CONSISTENT")
        self.assertEqual(report["counts"], {"gmail_sent": 1, "slack_receipts": 1, "discrepancies": 0})

    def test_changed_stable_id_conflict_holds(self):
        g = gmail()
        changed = copy.deepcopy(g["records"][0])
        changed["evidence_sha256"] = E2
        g["records"].append(changed)
        report = compile_report(g, slack(), policy(), as_of=NOW)
        self.assertEqual(report["status"], "HOLD")
        self.assertIn("GMAIL_STABLE_ID_CONFLICT:gm-1", report["hold_reasons"])

    def test_incomplete_snapshot_holds(self):
        report = compile_report(gmail(complete=False), slack(), policy(), as_of=NOW)
        self.assertEqual(report["status"], "HOLD")
        self.assertIn("GMAIL_SNAPSHOT_INCOMPLETE", report["hold_reasons"])

    def test_stale_snapshot_holds(self):
        report = compile_report(
            gmail(captured_at="2026-09-13T10:00:00Z"),
            slack(captured_at="2026-09-13T10:00:00Z"),
            policy(60),
            as_of=NOW,
        )
        self.assertEqual(report["status"], "HOLD")
        self.assertIn("GMAIL_SNAPSHOT_STALE", report["hold_reasons"])
        self.assertIn("SLACK_SNAPSHOT_STALE", report["hold_reasons"])

    def test_future_snapshot_and_record_hold(self):
        g = gmail(captured_at="2026-09-13T12:56:00Z")
        g["records"][0]["sent_at"] = "2026-09-13T12:56:00Z"
        report = compile_report(g, slack(), policy(), as_of=NOW)
        self.assertEqual(report["status"], "HOLD")
        self.assertIn("GMAIL_SNAPSHOT_FROM_FUTURE", report["hold_reasons"])
        self.assertIn("GMAIL_RECORD_FROM_FUTURE:gm-1", report["hold_reasons"])

    def test_record_after_snapshot_holds(self):
        g = gmail(captured_at="2026-09-13T12:53:00Z")
        report = compile_report(g, slack(), policy(), as_of=NOW)
        self.assertEqual(report["status"], "HOLD")
        self.assertIn("GMAIL_RECORD_AFTER_SNAPSHOT:gm-1", report["hold_reasons"])

    def test_bool_does_not_alias_int_policy(self):
        with self.assertRaises(ReconcileError):
            compile_report(gmail(), slack(), policy(True), as_of=NOW)

    def test_malformed_hash_rejected(self):
        g = gmail()
        g["records"][0]["recipient_sha256"] = "ABC"
        with self.assertRaises(ReconcileError):
            compile_report(g, slack(), policy(), as_of=NOW)

    def test_duplicate_json_keys_and_nonfinite_rejected(self):
        with self.assertRaises(ReconcileError):
            strict_json_loads('{"a":1,"a":2}')
        with self.assertRaises(ReconcileError):
            strict_json_loads('{"a":NaN}')

    def test_order_invariance(self):
        g_rows = gmail()["records"]
        g2 = copy.deepcopy(g_rows[0])
        g2["message_id"] = "gm-2"
        g2["recipient_sha256"] = H2
        g2["evidence_sha256"] = E2
        s_rows = slack()["records"]
        s2 = copy.deepcopy(s_rows[0])
        s2["event_id"] = "sl-2"
        s2["provider_message_id"] = "gm-2"
        s2["recipient_sha256"] = H2
        a = compile_report(gmail(g_rows + [g2]), slack(s_rows + [s2]), policy(), as_of=NOW)
        b = compile_report(gmail([g2] + g_rows), slack([s2] + s_rows), policy(), as_of=NOW)
        self.assertEqual(canonical_json(a), canonical_json(b))

    def test_tamper_policy_and_verifier_time_fences(self):
        report = compile_report(gmail(), slack(), policy(), as_of=NOW)
        changed = copy.deepcopy(report)
        changed["status"] = "RECONCILIATION_REQUIRED"
        self.assertFalse(verify_report(changed, gmail(), slack(), policy(), as_of=NOW))
        self.assertFalse(verify_report(report, gmail(), slack(), policy(10), as_of=NOW))
        later = datetime(2026, 9, 13, 14, 0, 0, tzinfo=timezone.utc)
        self.assertTrue(verify_report(report, gmail(), slack(), policy(), as_of=later))
        before_issue = datetime(2026, 9, 13, 12, 54, 59, tzinfo=timezone.utc)
        self.assertFalse(verify_report(report, gmail(), slack(), policy(), as_of=before_issue))
        malformed = copy.deepcopy(report)
        malformed["as_of"] = ["not", "a", "timestamp"]
        self.assertFalse(verify_report(malformed, gmail(), slack(), policy(), as_of=later))

    def test_cli_create_exclusive_and_symlink_refusal(self):
        root = Path(__file__).resolve().parent
        module = "revenue.outbound_transport_reconcile.reconcile"
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            for name, obj in (("gmail.json", gmail()), ("slack.json", slack()), ("policy.json", policy())):
                (td / name).write_text(json.dumps(obj), encoding="utf-8")
            out = td / "report.json"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(root)
            cmd = [
                sys.executable,
                "-m",
                module,
                "compile",
                "--gmail",
                str(td / "gmail.json"),
                "--slack",
                str(td / "slack.json"),
                "--policy",
                str(td / "policy.json"),
                "--report",
                str(out),
            ]
            first = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            verify_cmd = list(cmd)
            verify_cmd[3] = "verify"
            verified = subprocess.run(verify_cmd, env=env, capture_output=True, text=True, check=False)
            self.assertEqual(verified.returncode, 0, verified.stderr)
            self.assertIn("VERIFIED", verified.stdout)
            second = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
            self.assertEqual(second.returncode, 2)
            out.unlink()
            target = td / "target.json"
            target.write_text("x", encoding="utf-8")
            out.symlink_to(target)
            third = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
            self.assertEqual(third.returncode, 2)
            self.assertEqual(target.read_text(encoding="utf-8"), "x")


if __name__ == "__main__":
    unittest.main()
