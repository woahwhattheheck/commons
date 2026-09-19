import copy
import unittest

from tools.workfeed_poll_planner.core import (
    PlannerError,
    canonical_bytes,
    compile_plan,
)
from tools.workfeed_poll_planner.demo import sample_packet


class RecoveryIntegrationTests(unittest.TestCase):
    def _fresh_packet(self):
        packet = sample_packet()
        packet["request_budget"] = 2
        for row in packet["surfaces"]:
            row["last_success_utc"] = "2026-09-17T23:20:00Z"
            row["last_throttle_utc"] = None
            row["retry_after_seconds"] = 0
            row["consecutive_throttles"] = 0
            row["unread_estimate"] = 0
            row["backlog_estimate"] = 0
        return packet

    def test_zero_budget_never_reports_complete(self):
        packet = self._fresh_packet()
        packet["request_budget"] = 0
        plan = compile_plan(packet)
        self.assertEqual(plan["coverage"], "DEGRADED_BUDGET")
        self.assertEqual(plan["allocated_requests"], 0)

    def test_later_success_rejects_stale_throttle_state(self):
        packet = sample_packet()
        hot = packet["surfaces"][1]
        hot["last_success_utc"] = "2026-09-17T23:19:59Z"
        with self.assertRaises(PlannerError):
            compile_plan(packet)

    def test_input_order_is_semantically_invariant(self):
        packet = sample_packet()
        expected = compile_plan(packet)
        reordered = copy.deepcopy(packet)
        reordered["surfaces"] = list(reversed(reordered["surfaces"]))
        self.assertEqual(canonical_bytes(expected), canonical_bytes(compile_plan(reordered)))

    def test_bool_request_budget_is_rejected(self):
        packet = sample_packet()
        packet["request_budget"] = True
        with self.assertRaises(PlannerError):
            compile_plan(packet)

    def test_duplicate_surface_id_is_rejected(self):
        packet = sample_packet()
        packet["surfaces"][1]["surface_id"] = packet["surfaces"][0]["surface_id"]
        with self.assertRaises(PlannerError):
            compile_plan(packet)

    def test_exact_covered_generation_spends_no_request(self):
        packet = self._fresh_packet()
        for row in packet["surfaces"]:
            row["covered_by_generation"] = row["snapshot_generation"]
        plan = compile_plan(packet)
        self.assertEqual(plan["allocated_requests"], 0)
        self.assertEqual(plan["coverage"], "COMPLETE")
        self.assertTrue(all(row["decision"] == "SKIP_REDUNDANT" for row in plan["surfaces"]))

    def test_backoff_is_capped(self):
        packet = sample_packet()
        packet["backoff_base_seconds"] = 10
        packet["backoff_cap_seconds"] = 30
        hot = packet["surfaces"][1]
        hot["last_throttle_utc"] = "2026-09-17T23:19:40Z"
        hot["consecutive_throttles"] = 32
        hot["retry_after_seconds"] = 0
        hot["last_success_utc"] = "2026-09-17T23:18:00Z"
        plan = compile_plan(packet)
        row = next(r for r in plan["surfaces"] if r["surface_id"] == "hot-leads")
        self.assertEqual(row["next_safe_utc"], "2026-09-17T23:20:10Z")
        self.assertEqual(row["decision"], "HOLD_THROTTLED")


if __name__ == "__main__":
    unittest.main()
