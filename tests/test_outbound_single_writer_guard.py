from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "outbound_single_writer_guard.py"
spec = importlib.util.spec_from_file_location("outbound_single_writer_guard", MODULE_PATH)
guard = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = guard
spec.loader.exec_module(guard)


def h(ch: str) -> str:
    return ch * 64


def snapshot() -> dict:
    return {
        "schemaVersion": 1,
        "asOfUtc": "2026-09-16T14:00:00Z",
        "intent": {
            "intentKey": "ACME-ONE-SEND",
            "operationId": "ACME-OUTREACH-20260916",
            "opportunityKey": "ACME-RFP-42",
            "createdUtc": "2026-09-16T13:50:00Z",
            "route": {
                "channel": "EMAIL",
                "recipient": "buyer@example.com",
                "routeKey": "EMAIL:buyer@example.com",
            },
            "subjectSha256": h("a"),
            "bodySha256": h("b"),
        },
        "requests": [
            {
                "intentKey": "ACME-ONE-SEND",
                "operationId": "ACME-OUTREACH-20260916",
                "opportunityKey": "ACME-RFP-42",
                "routeKey": "EMAIL:buyer@example.com",
                "requesterSeat": "Z-TEST-A",
                "requestedUtc": "2026-09-16T13:51:00Z",
                "slackMessageTs": "1789566660.123456",
                "requestMessageSha256": h("c"),
            }
        ],
        "decisions": [
            {
                "intentKey": "ACME-ONE-SEND",
                "operationId": "ACME-OUTREACH-20260916",
                "opportunityKey": "ACME-RFP-42",
                "routeKey": "EMAIL:buyer@example.com",
                "requestSlackMessageTs": "1789566660.123456",
                "decision": "SELECTED",
                "selectedSeat": "Z-TEST-A",
                "leaseId": "MUSE-LEASE-42",
                "decidedUtc": "2026-09-16T13:52:00Z",
                "museMessageTs": "1789566720.654321",
                "museMessageSha256": h("d"),
            }
        ],
        "sendReceipts": [],
        "dnr": [],
        "sourceObservations": [h("e"), h("f"), h("1")],
    }


class GuardTests(unittest.TestCase):
    def test_ready_single_writer(self):
        report = guard.compile_report(snapshot())
        self.assertEqual(report["payload"]["result"], "READY_SINGLE_WRITER")
        self.assertEqual(report["payload"]["selection"]["selectedSeat"], "Z-TEST-A")
        self.assertTrue(guard.verify_report(snapshot(), report)["valid"])

    def test_no_request_holds(self):
        s = snapshot()
        s["requests"] = []
        s["decisions"] = []
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_NO_REQUEST")

    def test_no_decision_holds(self):
        s = snapshot()
        s["decisions"] = []
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_NO_MUSE_DECISION")

    def test_prior_send_holds(self):
        s = snapshot()
        s["sendReceipts"] = [{
            "intentKey": "ACME-ONE-SEND",
            "operationId": "ACME-OUTREACH-20260916",
            "opportunityKey": "ACME-RFP-42",
            "routeKey": "EMAIL:buyer@example.com",
            "senderSeat": "Z-TEST-A",
            "leaseId": "MUSE-LEASE-42",
            "providerMessageId": "gmail:abc123",
            "sentUtc": "2026-09-16T13:53:00Z",
        }]
        report = guard.compile_report(s)
        self.assertEqual(report["payload"]["result"], "HOLD_ALREADY_SENT")
        self.assertEqual(report["payload"]["selection"]["providerMessageId"], "gmail:abc123")

    def test_dnr_is_stronger_than_selection(self):
        s = snapshot()
        s["dnr"] = [{
            "opportunityKey": "ACME-RFP-42",
            "routeKey": "EMAIL:buyer@example.com",
            "createdUtc": "2026-09-16T13:49:00Z",
            "providerRef": "slack:dnr:1",
            "reasonCode": "HARD_NEGATIVE",
        }]
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_AFTER_DNR")

    def test_later_hold_supersedes_selection(self):
        s = snapshot()
        s["decisions"].append({
            "intentKey": "ACME-ONE-SEND",
            "operationId": "ACME-OUTREACH-20260916",
            "opportunityKey": "ACME-RFP-42",
            "routeKey": "EMAIL:buyer@example.com",
            "requestSlackMessageTs": "1789566660.123456",
            "decision": "HOLD",
            "selectedSeat": None,
            "leaseId": "MUSE-LEASE-43",
            "decidedUtc": "2026-09-16T13:53:00Z",
            "museMessageTs": "1789566780.654322",
            "museMessageSha256": h("2"),
        })
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_NO_MUSE_DECISION")

    def test_later_revocation_supersedes_selection(self):
        s = snapshot()
        d = deepcopy(s["decisions"][0])
        d.update({
            "decision": "REVOKED",
            "selectedSeat": None,
            "leaseId": "MUSE-LEASE-REVOKE",
            "decidedUtc": "2026-09-16T13:53:00Z",
            "museMessageTs": "1789566780.654322",
            "museMessageSha256": h("3"),
        })
        s["decisions"].append(d)
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_NO_MUSE_DECISION")

    def test_simultaneous_latest_decisions_hold(self):
        s = snapshot()
        d = deepcopy(s["decisions"][0])
        d.update({
            "leaseId": "MUSE-LEASE-X",
            "museMessageTs": "1789566720.654322",
            "museMessageSha256": h("4"),
        })
        s["decisions"].append(d)
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_MUSE_CONFLICT")

    def test_decision_must_bind_real_request(self):
        s = snapshot()
        s["decisions"][0]["requestSlackMessageTs"] = "1789560000.000001"
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_EVIDENCE_ORDERING")

    def test_decision_cannot_predate_request(self):
        s = snapshot()
        s["decisions"][0]["decidedUtc"] = "2026-09-16T13:50:00Z"
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_EVIDENCE_ORDERING")

    def test_selected_seat_must_match_bound_request(self):
        s = snapshot()
        s["decisions"][0]["selectedSeat"] = "Z-OTHER"
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_MUSE_CONFLICT")

    def test_two_requesters_can_be_adjudicated(self):
        s = snapshot()
        other = deepcopy(s["requests"][0])
        other.update({
            "requesterSeat": "Z-TEST-B",
            "slackMessageTs": "1789566661.123456",
            "requestMessageSha256": h("5"),
        })
        s["requests"].append(other)
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "READY_SINGLE_WRITER")

    def test_duplicate_request_body_holds(self):
        s = snapshot()
        other = deepcopy(s["requests"][0])
        other.update({
            "requesterSeat": "Z-TEST-B",
            "slackMessageTs": "1789566661.123456",
        })
        s["requests"].append(other)
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_REQUEST_CONFLICT")

    def test_rebound_intent_key_holds(self):
        s = snapshot()
        other = deepcopy(s["requests"][0])
        other["routeKey"] = "EMAIL:other@example.com"
        other["slackMessageTs"] = "1789566661.123456"
        other["requestMessageSha256"] = h("6")
        s["requests"].append(other)
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_SOURCE_CONFLICT")

    def test_future_request_holds(self):
        s = snapshot()
        s["requests"][0]["requestedUtc"] = "2026-09-16T14:00:01Z"
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_EVIDENCE_ORDERING")

    def test_future_decision_holds(self):
        s = snapshot()
        s["decisions"][0]["decidedUtc"] = "2026-09-16T14:00:01Z"
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_EVIDENCE_ORDERING")

    def test_future_send_holds(self):
        s = snapshot()
        s["sendReceipts"] = [{
            "intentKey": "ACME-ONE-SEND",
            "operationId": "ACME-OUTREACH-20260916",
            "opportunityKey": "ACME-RFP-42",
            "routeKey": "EMAIL:buyer@example.com",
            "senderSeat": "Z-TEST-A",
            "leaseId": "MUSE-LEASE-42",
            "providerMessageId": "gmail:abc123",
            "sentUtc": "2026-09-16T14:00:01Z",
        }]
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_EVIDENCE_ORDERING")

    def test_future_dnr_holds(self):
        s = snapshot()
        s["dnr"] = [{
            "opportunityKey": "ACME-RFP-42",
            "routeKey": "EMAIL:buyer@example.com",
            "createdUtc": "2026-09-16T14:00:01Z",
            "providerRef": "slack:dnr:1",
            "reasonCode": "HARD_NEGATIVE",
        }]
        self.assertEqual(guard.compile_report(s)["payload"]["result"], "HOLD_EVIDENCE_ORDERING")

    def test_public_authority_dict_mutation_cannot_authorize(self):
        s = snapshot()
        original = deepcopy(guard.AUTHORITY_FALSE)
        try:
            for key in list(guard.AUTHORITY_FALSE):
                guard.AUTHORITY_FALSE[key] = True
            report = guard.compile_report(s)
            self.assertTrue(all(v is False for v in report["payload"]["authorities"].values()))
        finally:
            guard.AUTHORITY_FALSE.clear()
            guard.AUTHORITY_FALSE.update(original)

    def test_public_authority_dict_rebind_cannot_authorize(self):
        s = snapshot()
        original = guard.AUTHORITY_FALSE
        try:
            guard.AUTHORITY_FALSE = {
                "externalSendAuthorized": True,
                "providerMutationAuthorized": True,
                "paymentAuthorized": True,
                "contractAuthorized": True,
                "submissionAuthorized": True,
                "revenueRecognized": True,
            }
            report = guard.compile_report(s)
            self.assertTrue(all(v is False for v in report["payload"]["authorities"].values()))
        finally:
            guard.AUTHORITY_FALSE = original

    def test_report_tamper_rejected(self):
        s = snapshot()
        report = guard.compile_report(s)
        report["payload"]["result"] = "HOLD_NO_REQUEST"
        self.assertFalse(guard.verify_report(s, report)["valid"])

    def test_resealed_report_tamper_rejected(self):
        s = snapshot()
        report = guard.compile_report(s)
        report["payload"]["result"] = "HOLD_NO_REQUEST"
        report["receiptSha256"] = guard.sha256_text(guard.canonical_json(report["payload"]))
        self.assertFalse(guard.verify_report(s, report)["valid"])

    def test_source_mutation_breaks_verification(self):
        s = snapshot()
        report = guard.compile_report(s)
        s["sourceObservations"][0] = h("9")
        self.assertFalse(guard.verify_report(s, report)["valid"])

    def test_input_order_does_not_change_receipt(self):
        s = snapshot()
        r1 = guard.compile_report(s)
        s["sourceObservations"].reverse()
        r2 = guard.compile_report(s)
        self.assertEqual(r1, r2)

    def test_duplicate_json_key_rejected(self):
        text = '{"schemaVersion":1,"schemaVersion":1}'
        with self.assertRaises(guard.GuardError) as ctx:
            guard.strict_json_loads(text)
        self.assertEqual(ctx.exception.code, "DUPLICATE_JSON_KEY")

    def test_float_rejected(self):
        with self.assertRaises(guard.GuardError) as ctx:
            guard.strict_json_loads('{"x":1.5}')
        self.assertEqual(ctx.exception.code, "FLOAT_NOT_ALLOWED")

    def test_nonfinite_rejected(self):
        with self.assertRaises(guard.GuardError) as ctx:
            guard.strict_json_loads('{"x":NaN}')
        self.assertEqual(ctx.exception.code, "NONFINITE_NUMBER")

    def test_unknown_field_rejected(self):
        s = snapshot()
        s["unexpected"] = 1
        with self.assertRaises(guard.GuardError):
            guard.compile_report(s)

    def test_bool_schema_version_rejected(self):
        s = snapshot()
        s["schemaVersion"] = True
        with self.assertRaises(guard.GuardError):
            guard.compile_report(s)

    def test_invalid_slack_ts_rejected(self):
        s = snapshot()
        s["requests"][0]["slackMessageTs"] = "bad"
        with self.assertRaises(guard.GuardError):
            guard.compile_report(s)

    def test_duplicate_source_observation_rejected(self):
        s = snapshot()
        s["sourceObservations"].append(s["sourceObservations"][0])
        with self.assertRaises(guard.GuardError):
            guard.compile_report(s)

    def test_duplicate_lease_rejected(self):
        s = snapshot()
        d = deepcopy(s["decisions"][0])
        d["museMessageTs"] = "1789566720.654322"
        d["museMessageSha256"] = h("7")
        s["decisions"].append(d)
        with self.assertRaises(guard.GuardError):
            guard.compile_report(s)

    def test_nonselected_decision_cannot_name_seat(self):
        s = snapshot()
        s["decisions"][0]["decision"] = "HOLD"
        with self.assertRaises(guard.GuardError):
            guard.compile_report(s)

    def test_selected_decision_requires_seat(self):
        s = snapshot()
        s["decisions"][0]["selectedSeat"] = None
        with self.assertRaises(guard.GuardError):
            guard.compile_report(s)

    def test_cli_round_trip(self):
        s = snapshot()
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            src = td / "snapshot.json"
            out = td / "report.json"
            src.write_text(json.dumps(s), encoding="utf-8")
            p = subprocess.run(
                [sys.executable, str(MODULE_PATH), "preflight", str(src), str(out)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(p.stdout.strip(), "READY_SINGLE_WRITER")
            v = subprocess.run(
                [sys.executable, str(MODULE_PATH), "verify", str(src), str(out)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(v.returncode, 0, v.stderr)
            self.assertEqual(v.stdout.strip(), "VERIFIED")

    def test_cli_refuses_overwrite(self):
        s = snapshot()
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            src = td / "snapshot.json"
            out = td / "report.json"
            src.write_text(json.dumps(s), encoding="utf-8")
            out.write_text("occupied", encoding="utf-8")
            p = subprocess.run(
                [sys.executable, str(MODULE_PATH), "preflight", str(src), str(out)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(p.returncode, 2)
            self.assertIn("OUTPUT_EXISTS", p.stderr)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unavailable")
    def test_cli_refuses_input_symlink(self):
        s = snapshot()
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            real = td / "real.json"
            link = td / "link.json"
            out = td / "report.json"
            real.write_text(json.dumps(s), encoding="utf-8")
            os.symlink(real, link)
            p = subprocess.run(
                [sys.executable, str(MODULE_PATH), "preflight", str(link), str(out)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(p.returncode, 2)
            self.assertIn("INPUT_OPEN_FAILED", p.stderr)


if __name__ == "__main__":
    unittest.main()
