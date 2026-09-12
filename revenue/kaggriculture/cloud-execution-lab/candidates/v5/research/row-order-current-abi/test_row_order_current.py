# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

import row_order_current as ro


def observation(**inventory):
    baseline = {item: 10000 for item in ro.RO_PARAMS}
    baseline.update(inventory)
    return {"market": {"inventory": baseline}}


def action(rows):
    return {
        "farmer": ["PASS"],
        "hands": [["PASS"]],
        "market": copy.deepcopy(rows),
    }


class RowOrderCurrentTests(unittest.TestCase):
    def test_requested_quantity_impact_reorders_only_leading_sells(self):
        original = action([
            ["SELL", "WHEAT", 10],
            ["SELL", "MILK", 10],
            ["BUY_SEED", "CARROT", 2],
            ["SELL", "STRAWBERRY", 10],
        ])
        before = copy.deepcopy(original)
        component = ro.RowOrderCurrentABI()
        result = component.transform(observation(), None, original)
        self.assertEqual(
            result["market"],
            [
                ["SELL", "MILK", 10],
                ["SELL", "WHEAT", 10],
                ["BUY_SEED", "CARROT", 2],
                ["SELL", "STRAWBERRY", 10],
            ],
        )
        self.assertEqual(original, before)
        self.assertEqual(component.diagnostics["leading_sell_count"], 2)
        self.assertEqual(component.diagnostics["status"], "applied")

    def test_falsey_row_is_a_hard_barrier_and_tail_is_byte_stable(self):
        rows = [
            ["SELL", "WHEAT", 10],
            [],
            ["SELL", "MILK", 10],
            {"engine_inert_suffix": True},
        ]
        original = action(rows)
        result = ro.transform(observation(), None, original)
        self.assertEqual(result, original)
        self.assertEqual(original["market"], rows)

    def test_nonpositive_sell_is_a_current_engine_barrier(self):
        original = action([
            ["SELL", "WHEAT", 0],
            ["SELL", "MILK", 10],
        ])
        self.assertEqual(ro.transform(observation(), None, original), original)

    def test_non_sell_ends_block_and_suffix_never_moves(self):
        original = action([
            ["SELL", "WHEAT", 10],
            ["BUY_PRODUCT", "CARROT", 1],
            ["SELL", "MILK", 10],
        ])
        self.assertEqual(ro.transform(observation(), None, original), original)

    def test_equal_impacts_preserve_exact_relative_order(self):
        original = action([
            ["SELL", "WHEAT", 10, "first"],
            ["SELL", "FERTILIZER", 10, "second"],
        ])
        # At inventory 10_000 both rows have impact 20 for quantity 10.
        result = ro.transform(observation(), None, original)
        self.assertEqual(result["market"], original["market"])

    def test_unknown_product_keeps_donor_zero_score_semantics(self):
        original = action([
            ["SELL", "UNKNOWN_PUBLIC_PRODUCT", 3],
            ["SELL", "MILK", 10],
        ])
        result = ro.transform(observation(), None, original)
        self.assertEqual(result["market"][0], ["SELL", "MILK", 10])
        self.assertEqual(result["market"][1], ["SELL", "UNKNOWN_PUBLIC_PRODUCT", 3])

    def test_market_params_override_is_identity(self):
        original = action([
            ["SELL", "WHEAT", 10],
            ["SELL", "MILK", 10],
        ])
        component = ro.RowOrderCurrentABI()
        result = component.transform(
            observation(),
            {"marketParams": {"custom": True}},
            original,
        )
        self.assertEqual(result, original)
        self.assertEqual(component.diagnostics["reason"], "marketParams_override")

    def test_empty_market_params_keeps_submitted_default_curve_path(self):
        original = action([
            ["SELL", "WHEAT", 10],
            ["SELL", "MILK", 10],
        ])
        result = ro.transform(observation(), {"marketParams": {}}, original)
        self.assertEqual(result["market"][0][:2], ["SELL", "MILK"])

    def test_malformed_quantity_and_inventory_fail_closed(self):
        for quantity in (True, 1.0, "10", -1):
            with self.subTest(quantity=quantity):
                original = action([
                    ["SELL", "WHEAT", quantity],
                    ["SELL", "MILK", 10],
                ])
                self.assertEqual(ro.transform(observation(), None, original), original)

        original = action([
            ["SELL", "WHEAT", 10],
            ["SELL", "MILK", 10],
        ])
        bad = observation()
        bad["market"]["inventory"]["WHEAT"] = True
        self.assertEqual(ro.transform(bad, None, original), original)

        missing = observation()
        del missing["market"]["inventory"]["WHEAT"]
        self.assertEqual(ro.transform(missing, None, original), original)

    def test_executable_prefix_only_preserves_inert_suffix(self):
        original = action([
            ["SELL", "WHEAT", 10],
            ["SELL", "MILK", 10],
            {"malformed_but_beyond_engine_prefix": object()},
        ])
        # Avoid comparing the opaque object through deepcopy identity; assert the
        # serialized row values around the suffix instead.
        suffix = original["market"][2]
        component = ro.RowOrderCurrentABI()
        result = component.transform(
            observation(),
            {"maxMarketOrdersPerTurn": 2},
            original,
        )
        self.assertEqual(result["market"][:2], [
            ["SELL", "MILK", 10],
            ["SELL", "WHEAT", 10],
        ])
        self.assertEqual(result["market"][2].keys(), suffix.keys())
        self.assertEqual(component.diagnostics["market_prefix_limit"], 2)

    def test_invalid_configuration_types_fail_closed(self):
        original = action([
            ["SELL", "WHEAT", 10],
            ["SELL", "MILK", 10],
        ])
        for config in ([], {"marketParams": []}, {"maxMarketOrdersPerTurn": True}):
            with self.subTest(config=config):
                self.assertEqual(ro.transform(observation(), config, original), original)


if __name__ == "__main__":
    unittest.main()
