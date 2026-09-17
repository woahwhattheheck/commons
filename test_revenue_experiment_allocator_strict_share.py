from __future__ import annotations

import unittest

from revenue.revenue_experiment_allocator.engine import compile_packet
from test_revenue_experiment_allocator import document, segment


class RevenueExperimentAllocatorStrictShareTests(unittest.TestCase):
    def test_nondivisible_share_cap_never_rounds_above_policy(self):
        a = segment("cap-a", available=100)
        b = segment("cap-b", available=100)
        packet = compile_packet(
            document([a, b], batch=3, share=5000, exploration=0)
        )
        by_id = {r["segment_id"]: r for r in packet["segments"]}
        self.assertEqual(packet["policy"]["per_segment_slot_cap"], 1)
        self.assertLessEqual(by_id["cap-a"]["allocated_slots"], 1)
        self.assertLessEqual(by_id["cap-b"]["allocated_slots"], 1)
        self.assertEqual(packet["summary"]["unallocated_slot_count"], 1)


if __name__ == "__main__":
    unittest.main()
