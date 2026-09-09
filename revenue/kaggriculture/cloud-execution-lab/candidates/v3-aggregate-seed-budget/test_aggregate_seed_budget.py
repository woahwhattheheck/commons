# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import unittest

from aggregate_seed_budget import cap_trailing_duplicate_seed
from audit_routes import scan_routes


COSTS = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}


class AggregateSeedBudgetTests(unittest.TestCase):
    def apply(self, action, *, stock=0, bound=5, cash=3000, cap=10):
        return cap_trailing_duplicate_seed(
            action,
            post_unit_seeds={"MELON": stock},
            remaining_demand={"MELON": bound},
            cash=cash,
            seed_costs=COSTS,
            max_orders=cap,
        )

    def test_trims_only_filled_tail_surplus(self):
        original = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["BUY_SEED", "MELON", 4], ["BUY_SEED", "MELON", 4]],
        }
        before = deepcopy(original)
        result, report = self.apply(original)
        self.assertEqual(original, before)
        self.assertIsNot(result, original)
        self.assertEqual(result["market"], [["BUY_SEED", "MELON", 4], ["BUY_SEED", "MELON", 1]])
        self.assertEqual(report["removed_filled_units"], 3)
        self.assertEqual(report["cash_saved"], 240)

    def test_partial_funding_that_does_not_overbuy_is_unchanged(self):
        action = {"market": [["BUY_SEED", "MELON", 4], ["BUY_SEED", "MELON", 4]]}
        result, report = self.apply(action, cash=240)
        self.assertIs(result, action)
        self.assertEqual(report["reason"], "within_aggregate_bound")
        self.assertEqual(report["aggregate_fill"], 3)

    def test_declines_when_surplus_is_not_local_to_tail(self):
        action = {"market": [["BUY_SEED", "MELON", 6], ["BUY_SEED", "MELON", 1]]}
        result, report = self.apply(action, bound=2)
        self.assertIs(result, action)
        self.assertEqual(report["reason"], "surplus_not_tail_local")

    def test_declines_across_sell_funding_ambiguity(self):
        action = {
            "market": [
                ["BUY_SEED", "MELON", 4],
                ["SELL", "CARROT", 5],
                ["BUY_SEED", "MELON", 4],
            ]
        }
        result, report = self.apply(action)
        self.assertIs(result, action)
        self.assertEqual(report["reason"], "ambiguous_prefix_order")
        self.assertEqual(report["ambiguous_index"], 1)

    def test_inactive_duplicate_does_not_activate(self):
        action = {
            "market": [
                ["BUY_SEED", "MELON", 4],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_SEED", "MELON", 4],
            ]
        }
        result, report = self.apply(action, cap=2)
        self.assertIs(result, action)
        self.assertEqual(report["reason"], "no_duplicate_target")

    def test_branch_compatible_bound_prevents_false_surplus(self):
        action = {"market": [["BUY_SEED", "MELON", 4], ["BUY_SEED", "MELON", 4]]}
        result, report = self.apply(action, bound=8)
        self.assertIs(result, action)
        self.assertEqual(report["reason"], "within_aggregate_bound")

    def test_zero_tail_becomes_exact_blank_and_is_idempotent(self):
        action = {"market": [["BUY_SEED", "MELON", 5], ["BUY_SEED", "MELON", 3], []]}
        result, report = self.apply(action, bound=5)
        self.assertTrue(report["changed"])
        self.assertEqual(result["market"], [["BUY_SEED", "MELON", 5], [], []])
        again, second = self.apply(result, bound=5)
        self.assertIs(again, result)
        self.assertFalse(second["changed"])

    def test_other_fixed_seed_rows_are_simulated_but_untouched(self):
        action = {
            "market": [
                ["BUY_SEED", "MELON", 3],
                ["BUY_SEED", "WHEAT", 2],
                ["BUY_SEED", "MELON", 4],
            ]
        }
        result, report = self.apply(action, bound=5, cash=1000)
        self.assertTrue(report["changed"])
        self.assertEqual(result["market"][0:2], action["market"][0:2])
        self.assertEqual(result["market"][2], ["BUY_SEED", "MELON", 2])

    def test_invalid_numeric_contract_fails_closed(self):
        action = {"market": [["BUY_SEED", "MELON", 4], ["BUY_SEED", "MELON", True]]}
        result, report = self.apply(action)
        self.assertIs(result, action)
        self.assertEqual(report["reason"], "tail_not_strict_seed")

    def test_route_scanner_separates_duplicate_from_tail_safe_shape(self):
        routes = {
            "a": [
                {"market": [["BUY_SEED", "MELON", 2], ["BUY_SEED", "MELON", 3]]},
                {"market": [["BUY_SEED", "MELON", 2], ["SELL", "WHEAT", 1], ["BUY_SEED", "MELON", 3]]},
            ],
            "b": [{"market": [["BUY_SEED", "WHEAT", 1]]}],
        }
        report = scan_routes(routes)
        self.assertEqual(report["route_count"], 2)
        self.assertEqual(report["duplicate_count"], 2)
        self.assertEqual(report["tail_safe_count"], 1)
        self.assertEqual(report["tail_safe"][0]["step"], 0)


if __name__ == "__main__":
    unittest.main()
