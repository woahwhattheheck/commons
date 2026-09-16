from __future__ import annotations

import importlib.util
import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

core_spec = importlib.util.spec_from_file_location("outbound_single_writer_guard", TOOLS / "outbound_single_writer_guard.py")
core = importlib.util.module_from_spec(core_spec)
assert core_spec and core_spec.loader
sys.modules[core_spec.name] = core
core_spec.loader.exec_module(core)

strict_spec = importlib.util.spec_from_file_location("outbound_single_writer_guard_strict", TOOLS / "outbound_single_writer_guard_strict.py")
strict = importlib.util.module_from_spec(strict_spec)
assert strict_spec and strict_spec.loader
sys.modules[strict_spec.name] = strict
strict_spec.loader.exec_module(strict)


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
            "route": {"channel": "EMAIL", "recipient": "buyer@example.com", "routeKey": "EMAIL:buyer@example.com"},
            "subjectSha256": h("a"),
            "bodySha256": h("b"),
        },
        "requests": [{
            "intentKey": "ACME-ONE-SEND",
            "operationId": "ACME-OUTREACH-20260916",
            "opportunityKey": "ACME-RFP-42",
            "routeKey": "EMAIL:buyer@example.com",
            "requesterSeat": "Z-TEST-A",
            "requestedUtc": "2026-09-16T13:51:00Z",
            "slackMessageTs": "1789566660.123456",
            "requestMessageSha256": h("c"),
        }],
        "decisions": [{
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
        }],
        "sendReceipts": [],
        "dnr": [],
        "sourceObservations": [h("e")],
    }


class StrictFenceTests(unittest.TestCase):
    def test_valid_snapshot_delegates_to_ready_core(self):
        report = strict.compile_report(snapshot())
        self.assertEqual(report["payload"]["result"], "READY_SINGLE_WRITER")
        self.assertTrue(strict.verify_report(snapshot(), report)["valid"])

    def test_wrong_route_request_holds_distinctly(self):
        s = snapshot()
        other = deepcopy(s["requests"][0])
        other.update({"routeKey": "EMAIL:other@example.com", "slackMessageTs": "1789566661.123456", "requestMessageSha256": h("f")})
        s["requests"].append(other)
        self.assertEqual(strict.compile_report(s)["payload"]["result"], "HOLD_ROUTE_MISMATCH")

    def test_wrong_route_decision_holds_distinctly(self):
        s = snapshot()
        s["decisions"][0]["routeKey"] = "EMAIL:other@example.com"
        self.assertEqual(strict.compile_report(s)["payload"]["result"], "HOLD_ROUTE_MISMATCH")

    def test_wrong_route_send_holds_distinctly(self):
        s = snapshot()
        s["sendReceipts"] = [{
            "intentKey": "ACME-ONE-SEND", "operationId": "ACME-OUTREACH-20260916", "opportunityKey": "ACME-RFP-42",
            "routeKey": "EMAIL:other@example.com", "senderSeat": "Z-TEST-A", "leaseId": "MUSE-LEASE-42",
            "providerMessageId": "gmail:wrongroute", "sentUtc": "2026-09-16T13:53:00Z",
        }]
        self.assertEqual(strict.compile_report(s)["payload"]["result"], "HOLD_ROUTE_MISMATCH")

    def test_rebound_operation_holds_as_source_conflict(self):
        s = snapshot()
        other = deepcopy(s["requests"][0])
        other.update({"operationId": "DIFFERENT-OPERATION", "slackMessageTs": "1789566661.123456", "requestMessageSha256": h("9")})
        s["requests"].append(other)
        self.assertEqual(strict.compile_report(s)["payload"]["result"], "HOLD_SOURCE_CONFLICT")


if __name__ == "__main__":
    unittest.main()
