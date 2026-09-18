import unittest

from tools.workfeed_poll_planner.core import PlannerError, compile_plan
from tools.workfeed_poll_planner.demo import sample_packet


class EvidenceTests(unittest.TestCase):
    def test_stale_snapshot_is_reported(self):
        packet = sample_packet()
        for row in packet["surfaces"]:
            row["snapshot_observed_utc"] = "2026-09-17T22:00:00Z"
            row["last_success_utc"] = "2026-09-17T21:59:00Z"
            row["last_throttle_utc"] = None
            row["retry_after_seconds"] = 0
            row["consecutive_throttles"] = 0
        self.assertEqual(compile_plan(packet)["coverage"], "DEGRADED_STALE_EVIDENCE")

    def test_future_snapshot_is_rejected(self):
        packet = sample_packet()
        packet["surfaces"][0]["snapshot_observed_utc"] = "2026-09-17T23:20:01Z"
        with self.assertRaises(PlannerError):
            compile_plan(packet)


if __name__ == "__main__":
    unittest.main()
