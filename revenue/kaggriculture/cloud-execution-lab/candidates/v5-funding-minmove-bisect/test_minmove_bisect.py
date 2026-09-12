# SPDX-License-Identifier: Apache-2.0
"""Exact-output regressions for V5 same-turn funding minimum-move bisection."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

import frozen_selected as fs  # noqa: E402


class SyntheticPrefix:
    """Monotone fixed-acquisition projector with an observable call count."""

    def __init__(self, threshold: int):
        self.threshold = int(threshold)
        self.calls = 0

    def __call__(self, orders, farm, private, market, shops, config, now,
                 rival_quantity, stop):
        del farm, private, market, shops, config, now, rival_quantity, stop
        self.calls += 1
        moved = 0
        if orders and orders[0] and orders[0][0] == "SELL":
            moved = int(orders[0][2])
        completed = 1 if moved >= self.threshold else 0
        return {
            "money": moved,
            "outcomes": {1: {"required": 1, "completed": completed,
                              "cost_per_unit": 10}},
            "unsupported_index": None,
            "shed": {},
            "inventory": {},
            "sale_stress": [],
        }


def run_with(projector, available: int, rival_quantity):
    orders = [[], ["HIRE"], ["SELL", "WOOL", int(available)]]
    with mock.patch.object(fs, "_market_prefix_state", side_effect=projector):
        return fs.fund_same_turn_acquisition(
            copy.deepcopy(orders),
            {"money": 0, "hires_today": 0, "unlocked_quadrants": ["NW"]},
            {"shed": {"WOOL": int(available)}},
            {"inventory": {"WOOL": fs.m.MARKET_I0}, "params": fs.m.MARKET_PARAMS},
            [],
            {"farmHandCostMult": 10, "shedCapacity": 100000},
            0,
            {"WOOL"},
            rival_quantity,
        )


class FundingMinMoveBisect(unittest.TestCase):
    def test_mapping_bisection_is_output_identical_to_callable_linear_oracle(self):
        # A callable intentionally retains the predecessor linear scan.  The
        # production V5 caller now supplies an immutable rival snapshot mapping,
        # which enables bisection.  Compare both paths over boundaries, interior
        # thresholds, and no-solution cases.
        for available in (1, 2, 3, 7, 8, 15, 16, 31, 32, 63, 64, 127, 255):
            thresholds = sorted({1, max(1, available // 2), available, available + 1})
            for threshold in thresholds:
                with self.subTest(available=available, threshold=threshold):
                    linear = SyntheticPrefix(threshold)
                    expected = run_with(linear, available, lambda _item: 0)
                    bisect = SyntheticPrefix(threshold)
                    actual = run_with(bisect, available, {"WOOL": 0})
                    self.assertEqual(actual, expected)

    def test_large_quantity_uses_logarithmic_prefix_probes(self):
        available = 1024
        threshold = 777
        linear = SyntheticPrefix(threshold)
        expected = run_with(linear, available, lambda _item: 0)
        self.assertEqual(linear.calls, threshold + 1)  # baseline + 1..threshold

        bisect = SyntheticPrefix(threshold)
        actual = run_with(bisect, available, {"WOOL": 0})
        self.assertEqual(actual, expected)
        # baseline + endpoint admission + binary first-true probes + final probe.
        self.assertLessEqual(bisect.calls, 14)
        self.assertLess(bisect.calls * 50, linear.calls)

    def test_real_prefix_completion_is_suffix_for_first_failing_fixed_buy(self):
        # Baseline HIRE completes; BUY_ANIMAL is therefore the first failing
        # acquisition. Moving more of the later CARROT sale into the preceding
        # empty slot cannot un-complete any earlier acquisition. Receipts are
        # positive/floor-admitting and the sale only frees shed capacity.
        available = 20
        original = [[], ["HIRE"], ["BUY_ANIMAL", "GOOSE", 1],
                    ["SELL", "CARROT", available]]
        farm = {"money": 10, "hires_today": 0, "unlocked_quadrants": ["NW"]}
        private = {"shed": {"CARROT": available}}
        market = {
            "inventory": {item: fs.m.MARKET_I0 for item in fs.m.PRODUCTS},
            "params": fs.m.MARKET_PARAMS,
        }
        config = {"farmHandCostMult": 10, "shedCapacity": available}
        outcomes = []
        for moved in range(1, available + 1):
            candidate = copy.deepcopy(original)
            candidate[0] = ["SELL", "CARROT", moved]
            candidate[3] = (["SELL", "CARROT", available - moved]
                            if moved < available else [])
            state = fs._market_prefix_state(
                candidate, farm, private, market, [], config, 0,
                {"CARROT": 0}, 2)
            outcomes.append(state["outcomes"][2]["completed"] == 1)
        self.assertIn(False, outcomes)
        self.assertIn(True, outcomes)
        first = outcomes.index(True)
        self.assertTrue(all(outcomes[first:]))

    def test_callable_api_keeps_linear_probe_order(self):
        # Preserve compatibility for external/stateful callback users.  Only a
        # mapping opts into the monotone first-true search.
        projector = SyntheticPrefix(9)
        result = run_with(projector, 20, lambda _item: 0)
        self.assertTrue(result[1]["applied"])
        self.assertEqual(result[1]["moved_quantity"], 9)
        self.assertEqual(projector.calls, 10)


if __name__ == "__main__":
    unittest.main()
