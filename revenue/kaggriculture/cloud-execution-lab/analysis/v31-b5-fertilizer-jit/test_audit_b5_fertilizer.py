# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_b5_fertilizer as audit  # noqa: E402


def _row(op="WATER"):
    return {"farmer": [op], "hands": [], "market": []}


class B5FertilizerTapeAuditTests(unittest.TestCase):
    def test_fake_census_counts_only_present_worker_slots(self):
        tape = [
            {"farmer": ["PASS"], "hands": [], "market": []},
            {"farmer": ["FERTILIZE"], "hands": [["PASS"]], "market": [["BUY_PRODUCT", "FERTILIZER", 1]]},
            {"farmer": ["WATER"], "hands": [["COLLECT_FERTILIZER"]], "market": [["SELL", "FERTILIZER", 1]]},
        ]
        before = copy.deepcopy(tape)
        report = audit.audit_tapes([tape])
        self.assertEqual(tape, before)
        self.assertEqual(report["route_count"], 1)
        self.assertEqual(report["total_steps"], 3)
        self.assertEqual(report["global_unit_counts"]["FERTILIZE"], 1)
        self.assertEqual(report["global_unit_counts"]["WATER"], 1)
        self.assertEqual(report["global_unit_counts"]["COLLECT_FERTILIZER"], 1)
        # Main farmer PASS at step 0 + hand PASS at step 1. The absent hand at
        # step 0 is not an actor and must not be counted as idle capacity.
        self.assertEqual(report["global_unit_counts"]["PASS"], 2)
        self.assertEqual(report["global_fertilizer_market_counts"]["BUY_PRODUCT:FERTILIZER"], 1)
        self.assertEqual(report["global_fertilizer_market_counts"]["SELL:FERTILIZER"], 1)

    def test_idle_streak_requires_six_literal_same_day_pass_rows(self):
        short = [{"farmer": ["PASS"], "market": []} for _ in range(5)]
        long = [{"farmer": ["PASS"], "market": []} for _ in range(6)]
        a = audit.audit_tapes([short])["routes"][0]["idle_streaks_ge_6"]
        b = audit.audit_tapes([long])["routes"][0]["idle_streaks_ge_6"]
        self.assertEqual(a, [])
        self.assertEqual(b, [{
            "worker": 0,
            "start_step": 0,
            "end_step": 5,
            "length": 6,
            "start_day": 0,
            "end_day": 0,
        }])

    def test_idle_streak_never_stitches_partial_days_across_midnight(self):
        for before, after in ((5, 1), (2, 4), (3, 3)):
            with self.subTest(before=before, after=after):
                tape = [_row() for _ in range(30)]
                for step in range(24 - before, 24):
                    tape[step] = _row("PASS")
                for step in range(24, 24 + after):
                    tape[step] = _row("PASS")
                streaks = audit.audit_tapes([tape])["routes"][0]["idle_streaks_ge_6"]
                self.assertEqual(streaks, [])

    def test_six_passes_after_midnight_remain_a_valid_same_day_window(self):
        tape = [_row() for _ in range(30)]
        for step in range(24, 30):
            tape[step] = _row("PASS")
        streaks = audit.audit_tapes([tape])["routes"][0]["idle_streaks_ge_6"]
        self.assertEqual(streaks, [{
            "worker": 0,
            "start_step": 24,
            "end_step": 29,
            "length": 6,
            "start_day": 1,
            "end_day": 1,
        }])

    def test_empty_or_missing_worker_action_never_manufactures_pass_capacity(self):
        empty = [{"farmer": [], "hands": [], "market": []} for _ in range(6)]
        missing = [{"hands": [], "market": []} for _ in range(6)]
        for tape in (empty, missing):
            report = audit.audit_tapes([tape])
            self.assertEqual(report["routes"][0]["idle_streaks_ge_6"], [])
            self.assertEqual(report["global_unit_counts"].get("PASS", 0), 0)
            self.assertEqual(report["global_unit_counts"]["MALFORMED"], 6)

    def test_malformed_hands_fail_closed_instead_of_disappearing(self):
        with self.assertRaisesRegex(TypeError, "row.hands"):
            audit.audit_tapes([[{"farmer": ["PASS"], "hands": {}, "market": []}]])

    def test_non_object_route_row_fails_closed(self):
        with self.assertRaises(TypeError):
            audit.audit_tapes([[None]])

    def test_current_r04_carrier_shape_and_determinism(self):
        tapes_a = audit.load_current_tapes()
        tapes_b = audit.load_current_tapes()
        self.assertEqual(len(tapes_a), audit.EXPECTED_ROUTES)
        self.assertTrue(all(len(t) == audit.EXPECTED_STEPS for t in tapes_a))
        self.assertEqual(tapes_a, tapes_b)
        report_a = audit.audit_current()
        report_b = audit.audit_current()
        self.assertEqual(report_a["route_census_sha256"], report_b["route_census_sha256"])
        self.assertEqual(report_a["route_count"], 13)
        self.assertEqual(report_a["total_steps"], 13 * 719)
        self.assertEqual(report_a["source"]["path"], "candidates/v3/overlay/r01_tapes.py")


if __name__ == "__main__":
    unittest.main()
