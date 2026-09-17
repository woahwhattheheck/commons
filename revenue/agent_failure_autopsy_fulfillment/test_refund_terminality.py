from __future__ import annotations

import unittest

from revenue.agent_failure_autopsy_fulfillment.core import compile_batch, verify_packet

D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64


def case(payment: str = "VERIFIED_PAID") -> dict:
    return {
        "case_ref": "CASE-REFUND",
        "payment": {
            "state": payment,
            "receipt_sha256": None if payment == "UNVERIFIED" else D1,
        },
        "intake": {
            "intended_outcome": "Produce a bounded diagnosis.",
            "observed_failure": "The bounded diagnosis could not be completed.",
            "stack": "Synthetic test harness",
            "first_error": "Evidence remained insufficient after clarification.",
            "evidence_items": [{"kind": "redacted_log", "sha256": D2, "bytes": 1}],
            "redaction_confirmed": True,
        },
        "operator": {
            "delivery_receipt_sha256": None,
            "refund_receipt_sha256": None,
            "refund_reason": "",
        },
    }


def batch(c: dict) -> dict:
    return {"schema": "agent-autopsy-fulfillment-batch/v1", "cases": [c]}


class RefundTerminalityTests(unittest.TestCase):
    def test_unsatisfied_refund_remains_active_priority_work(self):
        c = case()
        c["operator"]["refund_reason"] = "Cannot produce a defensible diagnosis."
        packet = compile_batch(batch(c))
        self.assertEqual(packet["cases"][0]["state"], "REFUND_REQUIRED")
        self.assertFalse(packet["cases"][0]["refund_satisfied"])
        self.assertEqual(
            packet["queue"],
            [{
                "case_ref": "CASE-REFUND",
                "state": "REFUND_REQUIRED",
                "case_digest": packet["cases"][0]["case_digest"],
            }],
        )
        self.assertTrue(verify_packet(packet))

    def test_refund_receipt_retires_case_from_active_queue(self):
        c = case()
        c["operator"]["refund_reason"] = "Cannot produce a defensible diagnosis."
        c["operator"]["refund_receipt_sha256"] = D3
        packet = compile_batch(batch(c))
        self.assertEqual(packet["cases"][0]["state"], "REFUND_REQUIRED")
        self.assertTrue(packet["cases"][0]["refund_satisfied"])
        self.assertEqual(packet["queue"], [])
        self.assertTrue(verify_packet(packet))

    def test_provider_refunded_state_retires_case_from_active_queue(self):
        packet = compile_batch(batch(case(payment="REFUNDED")))
        self.assertEqual(packet["cases"][0]["state"], "REFUND_REQUIRED")
        self.assertTrue(packet["cases"][0]["refund_satisfied"])
        self.assertEqual(packet["queue"], [])
        self.assertTrue(verify_packet(packet))


if __name__ == "__main__":
    unittest.main()
