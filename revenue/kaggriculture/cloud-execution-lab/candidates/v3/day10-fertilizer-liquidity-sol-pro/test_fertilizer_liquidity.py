# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

from fertilizer_liquidity import (
    ITEM,
    LiquiditySettings,
    executable_market_limit,
    propose_fertilizer_liquidity,
)


def observation(*, step=240, money=4000, inventory=1000):
    return {
        "step": step,
        "player": 0,
        "farms": [{"money": money}, {"money": 5000}],
        "market": {"inventory": {ITEM: inventory}},
    }


def constant(price):
    return lambda _inventory: price


class FertilizerLiquidityTests(unittest.TestCase):
    def settings(self, **updates):
        values = dict(
            start_day=8,
            end_day=10,
            reserve_units=24,
            minimum_unit_price=55,
            max_units_per_turn=64,
            liquidity_target=12000,
            rival_stress_units=32,
        )
        values.update(updates)
        return LiquiditySettings(**values)

    def propose(self, market, *, stock=100, obs=None, cfg=None, quote=None, settings=None):
        selected = {"farmer": ["PASS"], "hands": [], "market": copy.deepcopy(market)}
        result, report = propose_fertilizer_liquidity(
            obs or observation(),
            cfg or {"maxMarketOrdersPerTurn": 10, "turnsPerDay": 24},
            selected,
            post_unit_fertilizer=stock,
            quote=quote or constant(60),
            settings=settings or self.settings(),
        )
        return selected, result, report

    def test_official_market_limit_normalizes_zero_to_one(self):
        self.assertEqual(executable_market_limit({"maxMarketOrdersPerTurn": 0}), 1)
        self.assertEqual(executable_market_limit({"maxMarketOrdersPerTurn": "3"}), 3)

    def test_appends_after_inherited_rows_without_retiming(self):
        original, result, report = self.propose([["HIRE"]])
        self.assertTrue(report["changed"])
        self.assertEqual(result["market"][0], ["HIRE"])
        self.assertEqual(result["market"][1][0:2], ["SELL", ITEM])
        self.assertEqual(report["slot_mode"], "append")
        self.assertEqual(original["market"], [["HIRE"]])

    def test_uses_only_a_trailing_executable_blank(self):
        market = [["HIRE"], [], []]
        original, result, report = self.propose(
            market, cfg={"maxMarketOrdersPerTurn": 3, "turnsPerDay": 24}
        )
        self.assertTrue(report["changed"])
        self.assertEqual(report["slot"], 1)
        self.assertEqual(result["market"][2], [])
        self.assertEqual(original["market"], market)

    def test_rejects_interior_blank_before_later_inherited_order(self):
        original, result, report = self.propose(
            [["HIRE"], [], ["BUY_SEED", "MELON", 1]],
            cfg={"maxMarketOrdersPerTurn": 3, "turnsPerDay": 24},
        )
        self.assertIs(result, original)
        self.assertEqual(report["reason"], "no_final_executable_slot")

    def test_inactive_suffix_sell_is_not_execution_or_ownership(self):
        market = [[], ["SELL", ITEM, 90]]
        original, result, report = self.propose(
            market,
            cfg={"maxMarketOrdersPerTurn": 1, "turnsPerDay": 24},
            stock=100,
        )
        self.assertTrue(report["changed"])
        self.assertEqual(result["market"][0][0:2], ["SELL", ITEM])
        self.assertEqual(result["market"][1], ["SELL", ITEM, 90])
        self.assertEqual(report["inactive_suffix_rows"], 1)
        self.assertEqual(original["market"], market)

    def test_executable_incumbent_sale_retains_ownership(self):
        original, result, report = self.propose([["SELL", ITEM, 1]])
        self.assertIs(result, original)
        self.assertEqual(report["reason"], "incumbent_fertilizer_sale")

    def test_executable_fertilizer_purchase_is_a_hard_conflict(self):
        original, result, report = self.propose([["BUY_PRODUCT", ITEM, 1]])
        self.assertIs(result, original)
        self.assertEqual(report["reason"], "executable_fertilizer_purchase")

    def test_reserve_is_never_sold(self):
        original, result, report = self.propose([], stock=24)
        self.assertIs(result, original)
        self.assertEqual(report["reason"], "operating_reserve_not_exceeded")
        original, result, report = self.propose([], stock=25)
        self.assertEqual(result["market"], [["SELL", ITEM, 1]])

    def test_sale_is_capped_per_turn(self):
        _original, result, report = self.propose(
            [], stock=200, settings=self.settings(max_units_per_turn=17)
        )
        self.assertEqual(result["market"], [["SELL", ITEM, 17]])
        self.assertEqual(report["quantity"], 17)

    def test_smallest_lot_reaches_target_under_stress_quotes(self):
        _original, result, report = self.propose(
            [],
            stock=100,
            obs=observation(money=11880),
            quote=constant(60),
        )
        self.assertEqual(result["market"], [["SELL", ITEM, 2]])
        self.assertEqual(report["stressed_receipt"], 120)
        self.assertEqual(report["stressed_prices"], [60, 60])

    def test_quote_starts_after_named_rival_stress_lot(self):
        seen = []

        def quote(inv):
            seen.append(inv)
            return 60

        self.propose(
            [],
            stock=30,
            obs=observation(money=11940, inventory=100),
            quote=quote,
            settings=self.settings(rival_stress_units=32),
        )
        self.assertEqual(seen, [132])

    def test_each_admitted_sale_advances_public_inventory(self):
        seen = []

        def quote(inv):
            seen.append(inv)
            return 60

        _original, result, _report = self.propose(
            [], stock=100, obs=observation(money=11820, inventory=7), quote=quote
        )
        self.assertEqual(result["market"][0][2], 3)
        self.assertEqual(seen, [39, 40, 41])

    def test_stressed_price_floor_declines_without_mutation(self):
        original, result, report = self.propose([], quote=constant(54))
        self.assertIs(result, original)
        self.assertEqual(report["reason"], "stressed_price_floor_not_met")
        self.assertEqual(original["market"], [])

    def test_price_one_never_emits(self):
        original, result, report = self.propose(
            [], quote=constant(1), settings=self.settings(minimum_unit_price=2)
        )
        self.assertIs(result, original)
        self.assertEqual(report["reason"], "stressed_price_floor_not_met")

    def test_liquidity_target_stops_the_arm(self):
        original, result, report = self.propose([], obs=observation(money=12000))
        self.assertIs(result, original)
        self.assertEqual(report["reason"], "liquidity_target_already_met")

    def test_window_is_day_based_and_zero_indexed(self):
        original, result, report = self.propose([], obs=observation(step=191))
        self.assertIs(result, original)
        self.assertEqual(report["reason"], "outside_liquidity_window")
        _original, result, report = self.propose([], obs=observation(step=192))
        self.assertTrue(report["changed"])
        original, result, report = self.propose([], obs=observation(step=264))
        self.assertIs(result, original)
        self.assertEqual(report["reason"], "outside_liquidity_window")

    def test_quote_exception_fails_closed(self):
        def explode(_inventory):
            raise TypeError("bad quote")

        original, result, report = self.propose([], quote=explode)
        self.assertIs(result, original)
        self.assertTrue(report["reason"].startswith("fail_closed:"))

    def test_boolean_stock_fails_closed(self):
        original, result, report = self.propose([], stock=True)
        self.assertIs(result, original)
        self.assertIn("post_unit_fertilizer_is_boolean", report["reason"])

    def test_malformed_active_row_fails_closed(self):
        original, result, report = self.propose(["not-a-row"])
        self.assertIs(result, original)
        self.assertIn("malformed_market_row", report["reason"])

    def test_change_preserves_every_nonmarket_object_value(self):
        selected = {
            "farmer": ["WEST"],
            "hands": [["PASS"]],
            "market": [["HIRE"]],
            "extension": {"nested": [1, 2, 3]},
        }
        before = copy.deepcopy(selected)
        result, report = propose_fertilizer_liquidity(
            observation(),
            {"maxMarketOrdersPerTurn": 10, "turnsPerDay": 24},
            selected,
            post_unit_fertilizer=100,
            quote=constant(60),
            settings=self.settings(),
        )
        self.assertTrue(report["changed"])
        self.assertEqual(selected, before)
        self.assertEqual(result["farmer"], before["farmer"])
        self.assertEqual(result["hands"], before["hands"])
        self.assertEqual(result["extension"], before["extension"])

    def test_suffix_is_preserved_at_exact_indices(self):
        suffix = [["SELL", ITEM, 7], ["BUY_SEED", "WHEAT", 3]]
        market = [[], *copy.deepcopy(suffix)]
        _original, result, report = self.propose(
            market, cfg={"maxMarketOrdersPerTurn": 1, "turnsPerDay": 24}
        )
        self.assertTrue(report["changed"])
        self.assertEqual(result["market"][1:], suffix)

    def test_reversed_window_fails_closed(self):
        original, result, report = self.propose(
            [], settings=self.settings(start_day=11, end_day=10)
        )
        self.assertIs(result, original)
        self.assertIn("window_is_reversed", report["reason"])

    def test_nonintegral_quote_fails_closed(self):
        original, result, report = self.propose([], quote=constant(60.5))
        self.assertIs(result, original)
        self.assertIn("quote_not_finite_integer", report["reason"])


if __name__ == "__main__":
    unittest.main()
