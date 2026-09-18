import unittest

from tools.workfeed_poll_planner.core import compile_plan
from tools.workfeed_poll_planner.demo import sample_packet


class BudgetTests(unittest.TestCase):
    def test_one_request_budget_is_explicit(self):
        packet = sample_packet()
        packet["request_budget"] = 1
        plan = compile_plan(packet)
        self.assertEqual(plan["allocated_requests"], 1)
        self.assertTrue(any(row["reason"] == "request_budget_exhausted" for row in plan["surfaces"]))


if __name__ == "__main__":
    unittest.main()
