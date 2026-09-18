import copy
import unittest

from revenue.revenue_funnel_control.engine import FunnelError, compile_portfolio
from test_revenue_funnel_control import SHA_F, base_doc, event


class FunnelSettlementTests(unittest.TestCase):
    def test_unknown_amount_accepted_work_remains_economically_unfinished(self):
        doc = base_doc()
        op = doc["opportunities"][0]
        op["reference_amount_cents"] = None
        for row in op["events"]:
            if row["kind"] == "PROPOSAL_SENT":
                row["amount_cents"] = None
        compiled = next(x for x in compile_portfolio(doc)["opportunities"] if x["id"] == "workshare-1")
        self.assertEqual(compiled["stage"], "ACCEPTED_OR_MERGED")
        self.assertTrue(compiled["economically_unfinished"])
        self.assertIsNone(compiled["settlement_target_cents"])
        self.assertEqual(compiled["settlement_target_source"], "UNKNOWN")

    def test_invoice_amount_supersedes_reference_for_payment_completion(self):
        doc = base_doc()
        op = doc["opportunities"][1]
        op["reference_amount_cents"] = 9000
        op["events"].insert(
            -1,
            event(
                "invoice",
                "INVOICE_ISSUED",
                "2026-09-16T13:30:00Z",
                source="SPONSOR_MESSAGE",
                amount=10000,
                sha=SHA_F,
            ),
        )
        compiled = next(x for x in compile_portfolio(doc)["opportunities"] if x["id"] == "bounty-1")
        self.assertEqual(compiled["settlement_target_cents"], 10000)
        self.assertEqual(compiled["settlement_target_source"], "INVOICE_ISSUED")
        self.assertEqual(compiled["payment_received_cents"], 9000)
        self.assertEqual(compiled["stage"], "PARTIALLY_PAID")
        self.assertTrue(compiled["economically_unfinished"])

    def test_award_amount_supersedes_claim_amount(self):
        doc = base_doc()
        op = doc["opportunities"][1]
        award = next(x for x in op["events"] if x["kind"] == "AWARDED")
        payment = next(x for x in op["events"] if x["kind"] == "PAYMENT_RECEIVED")
        award["amount_cents"] = 8000
        payment["amount_cents"] = 8000
        compiled = next(x for x in compile_portfolio(doc)["opportunities"] if x["id"] == "bounty-1")
        self.assertEqual(compiled["settlement_target_cents"], 8000)
        self.assertEqual(compiled["settlement_target_source"], "AWARDED")
        self.assertEqual(compiled["stage"], "PAID")

    def test_same_second_predecessor_is_order_independent(self):
        doc = base_doc()
        op = doc["opportunities"][0]
        for row in op["events"]:
            if row["kind"] in {"QUALIFIED", "PROPOSAL_SENT", "ACCEPTED"}:
                row["observed_at"] = "2026-09-16T10:00:00Z"
        # Deliberately choose ids whose lexical order is reverse-stage order.
        next(x for x in op["events"] if x["kind"] == "QUALIFIED")["id"] = "z-qualified"
        next(x for x in op["events"] if x["kind"] == "PROPOSAL_SENT")["id"] = "m-proposal"
        next(x for x in op["events"] if x["kind"] == "ACCEPTED")["id"] = "a-accepted"
        compiled = next(x for x in compile_portfolio(doc)["opportunities"] if x["id"] == "workshare-1")
        self.assertEqual(compiled["stage"], "ACCEPTED_OR_MERGED")


if __name__ == "__main__":
    unittest.main()
