import unittest

from tools.workfeed_poll_planner.demo import sample_packet
from tools.workfeed_poll_planner.core import compile_plan, verify_plan


class WorkfeedPlannerTests(unittest.TestCase):
    def test_demo_packet(self):
        packet = sample_packet()
        plan = compile_plan(packet)
        self.assertEqual(plan["coverage"], "DEGRADED_RATE_LIMIT")
        self.assertEqual(plan["allocated_requests"], 2)
        self.assertTrue(verify_plan(packet, plan))


if __name__ == "__main__":
    unittest.main()
