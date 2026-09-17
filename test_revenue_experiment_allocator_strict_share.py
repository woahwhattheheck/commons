from __future__ import annotations

import unittest

from revenue.revenue_experiment_allocator.engine import AllocationError, compile_packet
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

    def test_semantic_segment_aliases_cannot_multiply_hard_cap(self):
        a = segment("winner-a", available=100)
        b = segment("winner-b", available=100)
        b["offer_id"] = a["offer_id"]
        b["route_kind"] = a["route_kind"]
        b["audience_label"] = a["audience_label"]
        self.assertNotEqual(a["evidence_ref"], b["evidence_ref"])
        self.assertNotEqual(a["evidence_sha256"], b["evidence_sha256"])
        with self.assertRaisesRegex(AllocationError, "duplicate semantic segment"):
            compile_packet(document([a, b], batch=10, share=3000, exploration=0))

    def test_semantic_identity_normalizes_case_spacing_and_nfkc(self):
        a = segment("winner-a", available=100)
        a["offer_id"] = "Offer-Alpha"
        a["audience_label"] = "North America Buyers"
        b = segment("winner-b", available=100)
        b["offer_id"] = "  ＯＦＦＥＲ-ＡＬＰＨＡ  "
        b["route_kind"] = a["route_kind"]
        b["audience_label"] = " north   america buyers "
        with self.assertRaisesRegex(AllocationError, "duplicate semantic segment"):
            compile_packet(document([a, b], batch=10, share=3000, exploration=0))

    def test_unicode_format_alias_is_rejected_at_identity_boundary(self):
        a = segment("winner-a", available=100)
        a["offer_id"] = "offer-alpha"
        b = segment("winner-b", available=100)
        b["offer_id"] = "offer-\u200balpha"
        b["route_kind"] = "CONTACT_FORM"
        with self.assertRaisesRegex(AllocationError, "Unicode control/format"):
            compile_packet(document([a, b], batch=10, share=3000, exploration=0))

    def test_distinct_semantic_segments_remain_distinct(self):
        a = segment("winner-a", available=100)
        b = segment("winner-b", available=100)
        b["offer_id"] = a["offer_id"]
        b["audience_label"] = a["audience_label"]
        b["route_kind"] = "CONTACT_FORM"
        packet = compile_packet(document([a, b], batch=10, share=3000, exploration=0))
        by_id = {r["segment_id"]: r for r in packet["segments"]}
        self.assertLessEqual(by_id["winner-a"]["allocated_slots"], 3)
        self.assertLessEqual(by_id["winner-b"]["allocated_slots"], 3)
        self.assertEqual(packet["summary"]["unallocated_slot_count"], 4)


if __name__ == "__main__":
    unittest.main()
