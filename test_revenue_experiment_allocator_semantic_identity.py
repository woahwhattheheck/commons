from __future__ import annotations

import subprocess
import sys
import unittest

from revenue.revenue_experiment_allocator.engine import AllocationError, compile_packet
from test_revenue_experiment_allocator import document, segment


def aliased_segments():
    a = segment("winner-a", available=100)
    b = segment("winner-b", available=100)
    b["offer_id"] = a["offer_id"]
    b["route_kind"] = a["route_kind"]
    b["audience_label"] = a["audience_label"]
    return a, b


class RevenueExperimentAllocatorSemanticIdentityTests(unittest.TestCase):
    def test_distinct_ids_and_evidence_cannot_multiply_one_semantic_segment_cap(self):
        a, b = aliased_segments()
        self.assertNotEqual(a["segment_id"], b["segment_id"])
        self.assertNotEqual(a["evidence_ref"], b["evidence_ref"])
        self.assertNotEqual(a["evidence_sha256"], b["evidence_sha256"])
        with self.assertRaisesRegex(AllocationError, "duplicate semantic segment identity"):
            compile_packet(document([a, b], batch=10, share=3000, exploration=0))

    def test_nfkc_case_and_whitespace_aliases_fail_closed(self):
        a = segment("unicode-a", available=100)
        b = segment("unicode-b", available=100)
        a["offer_id"] = "Offer-A"
        a["audience_label"] = "Health Systems"
        b["offer_id"] = "ＯＦＦＥＲ－Ａ"
        b["audience_label"] = "  HEALTH   SYSTEMS  "
        with self.assertRaisesRegex(AllocationError, "duplicate semantic segment identity"):
            compile_packet(document([a, b], batch=10, share=3000, exploration=0))

    def test_format_control_in_semantic_identity_is_rejected(self):
        bad = segment("format-control")
        bad["audience_label"] = "Health\u200bSystems"
        with self.assertRaisesRegex(AllocationError, "canonical semantic identity text"):
            compile_packet(document([bad], batch=1, share=10_000, exploration=0))

    def test_distinct_audiences_remain_distinct_segments(self):
        a = segment("audience-a", available=100)
        b = segment("audience-b", available=100)
        b["offer_id"] = a["offer_id"]
        b["route_kind"] = a["route_kind"]
        a["audience_label"] = "Health Systems"
        b["audience_label"] = "Independent Pharmacies"
        packet = compile_packet(document([a, b], batch=10, share=3000, exploration=0))
        by_id = {row["segment_id"]: row for row in packet["segments"]}
        self.assertLessEqual(by_id["audience-a"]["allocated_slots"], 3)
        self.assertLessEqual(by_id["audience-b"]["allocated_slots"], 3)
        self.assertEqual(packet["summary"]["unallocated_slot_count"], 4)

    def test_complete_semantic_identity_suite_under_optimized_python(self):
        if sys.flags.optimize:
            return
        proc = subprocess.run(
            [
                sys.executable,
                "-O",
                "-m",
                "unittest",
                "-q",
                "test_revenue_experiment_allocator_semantic_identity.py",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("OK", proc.stderr + proc.stdout)


if __name__ == "__main__":
    unittest.main()
