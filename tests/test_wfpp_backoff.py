import unittest

from tools.workfeed_poll_planner.core import compile_plan
from tools.workfeed_poll_planner.demo import sample_packet


class BackoffTests(unittest.TestCase):
    def test_retry_window_holds_due_surface(self):
        plan = compile_plan(sample_packet())
        hot = next(row for row in plan["surfaces"] if row["surface_id"] == "hot-leads")
        self.assertEqual(hot["decision"], "HOLD_THROTTLED")
        self.assertEqual(hot["next_safe_utc"], "2026-09-17T23:20:05Z")

    def test_boundary_releases_surface(self):
        packet = sample_packet()
        packet["surfaces"][1]["last_throttle_utc"] = "2026-09-17T23:19:52Z"
        plan = compile_plan(packet)
        hot = next(row for row in plan["surfaces"] if row["surface_id"] == "hot-leads")
        self.assertNotEqual(hot["decision"], "HOLD_THROTTLED")


if __name__ == "__main__":
    unittest.main()
