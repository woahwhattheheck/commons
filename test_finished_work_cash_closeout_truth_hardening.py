import unittest

from revenue.finished_work_cash_closeout.closeout import SCHEMA, build_closeout


def item(**overrides):
    value = {
        "work_id": "competition-entry-7",
        "payer_key": "example-sponsor",
        "opportunity_key": "competition-2026",
        "payment_unit_key": "entry-7",
        "route_key": "provider:competition-2026",
        "currency": "USD",
        "advertised_amount_minor": 50000,
        "advertised_reward_evidence": ["provider:terms#reward"],
        "eligibility_state": "ELIGIBLE",
        "eligibility_evidence": ["provider:terms#eligibility"],
        "completion_kind": "SUBMITTED",
        "completion_receipts": ["provider:entry-7#submitted"],
        "provider_state": "AWARDED",
        "provider_state_evidence": ["provider:entry-7#awarded"],
        "payment_state": "UNPAID",
        "payment_state_evidence": ["provider:entry-7#payment-state"],
        "payment_receipts": [],
        "prior_payment_request_receipts": [],
        "muse_owner": None,
        "dnr": False,
    }
    value.update(overrides)
    return value


def packet(value):
    return build_closeout({"schema": SCHEMA, "items": [value]})["groups"][0]


class CashCloseoutTruthHardeningTests(unittest.TestCase):
    def test_pending_payment_without_retained_state_evidence_fails_closed(self):
        group = packet(item(payment_state="PENDING", payment_state_evidence=[]))
        self.assertEqual(group["status"], "EVIDENCE_GAP")
        self.assertIn("MISSING_PENDING_PAYMENT_EVIDENCE", group["reason_codes"])
        self.assertTrue(all(value is False for value in group["authority"].values()))

    def test_pending_payment_with_retained_state_evidence_waits_provider(self):
        group = packet(item(payment_state="PENDING", payment_state_evidence=["provider:pending-payment"]))
        self.assertEqual(group["status"], "WAIT_PROVIDER")
        self.assertIn("PAYMENT_PENDING", group["reason_codes"])

    def test_submitted_work_can_be_payable_after_provider_award(self):
        group = packet(item())
        self.assertEqual(group["status"], "READY_FOR_MUSE_ELECTION")
        self.assertEqual(group["reason_codes"], ["PAYABLE_EVIDENCE_COMPLETE", "UNPAID_EVIDENCE_RETAINED"])
        self.assertTrue(all(value is False for value in group["authority"].values()))


if __name__ == "__main__":
    unittest.main()
