import copy
import unittest

from revenue.revenue_funnel_control.engine import FunnelError, compile_portfolio
from test_revenue_funnel_control import SHA_F, base_doc, event


class FunnelSameTimeClaimTests(unittest.TestCase):
    def _row(self, document, opportunity_id):
        return next(row for row in compile_portfolio(document)["opportunities"] if row["id"] == opportunity_id)

    def test_same_time_conflicting_invoice_amounts_fail_under_id_swap(self):
        for first_id, second_id in (("a-invoice", "z-invoice"), ("z-invoice", "a-invoice")):
            with self.subTest(ids=(first_id, second_id)):
                doc = base_doc()
                op = next(row for row in doc["opportunities"] if row["id"] == "bounty-1")
                payment_index = next(i for i, row in enumerate(op["events"]) if row["kind"] == "PAYMENT_RECEIVED")
                op["events"].insert(
                    payment_index,
                    event(first_id, "INVOICE_ISSUED", "2026-09-16T13:30:00Z", source="SPONSOR_MESSAGE", amount=8000, sha=SHA_F),
                )
                op["events"].insert(
                    payment_index + 1,
                    event(second_id, "INVOICE_ISSUED", "2026-09-16T13:30:00Z", source="SPONSOR_MESSAGE", amount=10000, sha="1" * 64),
                )
                with self.assertRaises(FunnelError):
                    compile_portfolio(doc)

    def test_same_time_conflicting_awards_fail_under_id_swap(self):
        for first_id, second_id in (("a-award", "z-award"), ("z-award", "a-award")):
            with self.subTest(ids=(first_id, second_id)):
                doc = base_doc()
                op = next(row for row in doc["opportunities"] if row["id"] == "bounty-1")
                original = next(row for row in op["events"] if row["kind"] == "AWARDED")
                original["id"] = first_id
                original["amount_cents"] = 8000
                original["sha256"] = SHA_F
                op["events"].append(
                    event(second_id, "AWARDED", original["observed_at"], source="SPONSOR_MESSAGE", amount=10000, sha="1" * 64)
                )
                with self.assertRaises(FunnelError):
                    compile_portfolio(doc)

    def test_shared_proposal_claim_tier_distinct_claims_fail_even_same_amount(self):
        for proposal_id, claim_id in (("a-proposal", "z-claim"), ("z-proposal", "a-claim")):
            with self.subTest(ids=(proposal_id, claim_id)):
                doc = base_doc()
                op = next(row for row in doc["opportunities"] if row["id"] == "workshare-1")
                proposal = next(row for row in op["events"] if row["kind"] == "PROPOSAL_SENT")
                proposal["id"] = proposal_id
                proposal["sha256"] = SHA_F
                op["events"].append(
                    event(
                        claim_id,
                        "CLAIM_SUBMITTED",
                        proposal["observed_at"],
                        source="BUYER_MESSAGE",
                        amount=proposal["amount_cents"],
                        sha="1" * 64,
                    )
                )
                with self.assertRaises(FunnelError):
                    compile_portfolio(doc)

    def test_equal_same_kind_latest_claims_have_id_invariant_economics(self):
        stages = []
        targets = []
        sources = []
        for first_id, second_id in (("a-invoice", "z-invoice"), ("z-invoice", "a-invoice")):
            doc = base_doc()
            op = next(row for row in doc["opportunities"] if row["id"] == "bounty-1")
            payment_index = next(i for i, row in enumerate(op["events"]) if row["kind"] == "PAYMENT_RECEIVED")
            op["events"].insert(
                payment_index,
                event(first_id, "INVOICE_ISSUED", "2026-09-16T13:30:00Z", source="SPONSOR_MESSAGE", amount=9000, sha=SHA_F),
            )
            op["events"].insert(
                payment_index + 1,
                event(second_id, "INVOICE_ISSUED", "2026-09-16T13:30:00Z", source="SPONSOR_MESSAGE", amount=9000, sha="1" * 64),
            )
            compiled = self._row(doc, "bounty-1")
            stages.append(compiled["stage"])
            targets.append(compiled["settlement_target_cents"])
            sources.append(compiled["settlement_target_source"])
        self.assertEqual(stages, ["PAID", "PAID"])
        self.assertEqual(targets, [9000, 9000])
        self.assertEqual(sources, ["INVOICE_ISSUED", "INVOICE_ISSUED"])


if __name__ == "__main__":
    unittest.main()
