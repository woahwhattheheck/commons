# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_b5_fertilizer as audit  # noqa: E402


def row(action=None, *, hands=None):
    out = {"farmer": action if action is not None else ["NORTH"], "market": []}
    if hands is not None:
        out["hands"] = hands
    return out


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
        # Main farmer PASS at step 0 + hand PASS at step 1.  The absent hand at
        # step 0 is not an actor and must not be counted as idle capacity.
        self.assertEqual(report["global_unit_counts"]["PASS"], 2)
        self.assertEqual(report["global_fertilizer_market_counts"]["BUY_PRODUCT:FERTILIZER"], 1)
        self.assertEqual(report["global_fertilizer_market_counts"]["SELL:FERTILIZER"], 1)

    def test_idle_streak_requires_six_literal_pass_rows(self):
        short = [{"farmer": ["PASS"], "market": []} for _ in range(5)]
        long = [{"farmer": ["PASS"], "market": []} for _ in range(6)]
        a = audit.audit_tapes([short])["routes"][0]["same_day_idle_streaks_ge_6"]
        b = audit.audit_tapes([long])["routes"][0]["same_day_idle_streaks_ge_6"]
        self.assertEqual(a, [])
        self.assertEqual(b, [{
            "worker": 0,
            "start_step": 0,
            "end_step": 5,
            "length": 6,
            "start_day": 0,
            "end_day": 0,
        }])

    def _cross_midnight(self, before: int, after: int):
        tape = [row() for _ in range(48)]
        for step in range(24 - before, 24 + after):
            tape[step] = row(["PASS"])
        return audit.audit_tapes([tape])["routes"][0]["same_day_idle_streaks_ge_6"]

    def test_cross_midnight_5_plus_1_is_not_idle_window(self):
        self.assertEqual(self._cross_midnight(5, 1), [])

    def test_cross_midnight_2_plus_4_is_not_idle_window(self):
        self.assertEqual(self._cross_midnight(2, 4), [])

    def test_cross_midnight_3_plus_3_is_not_idle_window(self):
        self.assertEqual(self._cross_midnight(3, 3), [])

    def test_same_day_six_closes_at_midnight(self):
        tape = [row() for _ in range(48)]
        for step in range(18, 25):
            tape[step] = row(["PASS"])
        windows = audit.audit_tapes([tape])["routes"][0]["same_day_idle_streaks_ge_6"]
        self.assertEqual(windows, [{
            "worker": 0,
            "start_step": 18,
            "end_step": 23,
            "length": 6,
            "start_day": 0,
            "end_day": 0,
        }])

    def test_non_object_route_row_fails_closed(self):
        with self.assertRaises(TypeError):
            audit.audit_tapes([[None]])

    def test_missing_farmer_fails_closed(self):
        with self.assertRaises(TypeError):
            audit.audit_tapes([[{"hands": [], "market": []}]])

    def test_empty_or_malformed_worker_action_fails_closed(self):
        for action in ([], None, [1], [""]):
            with self.subTest(action=action):
                with self.assertRaises(TypeError):
                    audit.audit_tapes([[{"farmer": action, "hands": [], "market": []}]])

    def test_nonlist_hands_fails_closed(self):
        with self.assertRaises(TypeError):
            audit.audit_tapes([[{"farmer": ["PASS"], "hands": "PASS", "market": []}]])

    def test_malformed_hand_action_fails_closed(self):
        with self.assertRaises(TypeError):
            audit.audit_tapes([[{"farmer": ["PASS"], "hands": [[]], "market": []}]])

    def test_current_r04_carrier_shape_and_determinism(self):
        tapes_a = audit.load_current_tapes()
        tapes_b = audit.load_current_tapes()
        self.assertEqual(len(tapes_a), audit.EXPECTED_ROUTES)
        self.assertTrue(all(len(t) == audit.EXPECTED_STEPS for t in tapes_a))
        self.assertEqual(tapes_a, tapes_b)
        report_a = audit.audit_current()
        report_b = audit.audit_current()
        self.assertEqual(report_a["schema"], 2)
        self.assertEqual(report_a["route_census_sha256"], report_b["route_census_sha256"])
        self.assertEqual(report_a["route_count"], 13)
        self.assertEqual(report_a["total_steps"], 13 * 719)
        self.assertEqual(report_a["source"]["path"], "candidates/v3/overlay/r01_tapes.py")
        for route_report in report_a["routes"]:
            for window in route_report["same_day_idle_streaks_ge_6"]:
                self.assertEqual(window["start_day"], window["end_day"])


if __name__ == "__main__":
    unittest.main()
