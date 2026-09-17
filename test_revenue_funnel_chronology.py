import unittest

from revenue.revenue_funnel_control.engine import FunnelError, compile_portfolio
from test_revenue_funnel_control import base_doc


class FunnelChronologyTests(unittest.TestCase):
    def test_each_commercial_milestone_requires_prior_stage(self):
        cases = [
            ("workshare-1", "PROPOSAL_SENT", "2026-09-16T09:00:00Z"),
            ("workshare-1", "ACCEPTED", "2026-09-16T10:30:00Z"),
            ("bounty-1", "AWARDED", "2026-09-16T11:30:00Z"),
            ("bounty-1", "PAYMENT_RECEIVED", "2026-09-16T12:30:00Z"),
        ]
        for opportunity_id, kind, at in cases:
            with self.subTest(kind=kind):
                doc = base_doc()
                op = next(item for item in doc["opportunities"] if item["id"] == opportunity_id)
                target = next(item for item in op["events"] if item["kind"] == kind)
                target["observed_at"] = at
                with self.assertRaises(FunnelError):
                    compile_portfolio(doc)


if __name__ == "__main__":
    unittest.main()
