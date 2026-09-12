# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

from market_microstack_current import (
    ADVANCE_START,
    L3_THRESHOLD,
    PRODUCTS,
    SALE_HORIZON,
)
from market_microstack_current_safe import R04MarketMicrostackCurrentABI


DEFAULT_PRICES = {
    "WHEAT": 25,
    "CARROT": 35,
    "TOMATO": 60,
    "STRAWBERRY": 120,
    "MELON": 250,
    "EGG": 50,
    "MILK": 160,
    "WOOL": 200,
    "FERTILIZER": 100,
}


def action(*, market=None, farmer=None, hands=None):
    return {
        "farmer": ["PASS"] if farmer is None else copy.deepcopy(farmer),
        "hands": [] if hands is None else copy.deepcopy(hands),
        "market": [] if market is None else copy.deepcopy(market),
    }


def shed(**updates):
    result = {item: 0 for item in PRODUCTS}
    result.update(updates)
    return result


def observation(
    step,
    *,
    same_rival=False,
    farmer=(0, 0),
    rival_farmer=(1, 0),
    hands=0,
    inventories=None,
    prices=None,
):
    ours = list(farmer)
    theirs = list(farmer if same_rival else rival_farmer)
    hand_positions = [[0, 0] for _ in range(hands)]
    if inventories is None:
        inventories = [{} for _ in range(hands + 1)]
    return {
        "step": step,
        "player": 0,
        "farms": [
            {"farmer": ours, "hands": copy.deepcopy(hand_positions)},
            {"farmer": theirs, "hands": []},
        ],
        "private": {"inventories": copy.deepcopy(inventories)},
        "market": {"prices": dict(DEFAULT_PRICES if prices is None else prices)},
    }


def future_range(start, end, market_by_step=None, farmer_by_step=None):
    market_by_step = {} if market_by_step is None else market_by_step
    farmer_by_step = {} if farmer_by_step is None else farmer_by_step
    return {
        step: action(
            market=market_by_step.get(step, []),
            farmer=farmer_by_step.get(step, ["PASS"]),
        )
        for step in range(start, end + 1)
    }


class MarketMicrostackTests(unittest.TestCase):
    def test_submitted_constants_are_fixed(self):
        self.assertEqual(ADVANCE_START, 288)
        self.assertEqual(SALE_HORIZON, 8)
        self.assertEqual(L3_THRESHOLD, 648)

    def test_flags_require_exact_bool(self):
        with self.assertRaises(TypeError):
            R04MarketMicrostackCurrentABI(sale_window=1)

    def test_default_off_is_exact_identity(self):
        component = R04MarketMicrostackCurrentABI()
        selected = action(market=[["SELL", "CARROT", 2]])
        before = copy.deepcopy(selected)
        result, report = component.sale_window_transform(
            observation(300), None, selected, post_unit_shed=shed(CARROT=2)
        )
        self.assertEqual(result, before)
        self.assertEqual(selected, before)
        self.assertEqual(report["reason"], "disabled")

    def test_e184_h8_reserves_authored_future_sales_and_debt(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True,
            sale_fertilizer=True,
            no_late_sale_advance=True,
        )
        future = future_range(
            301,
            308,
            market_by_step={
                301: [["SELL", "CARROT", 2]],
                302: [["SELL", "CARROT", 3]],
            },
        )
        result, report = component.sale_window_transform(
            observation(300),
            None,
            action(),
            post_unit_shed=shed(CARROT=4),
            future_actions=future,
            queued_commands=[],
        )
        self.assertEqual(result["market"], [["SELL", "CARROT", 4]])
        self.assertEqual(
            report["debts_after"],
            {301: {"CARROT": 2}, 302: {"CARROT": 2}},
        )

    def test_sale_fertilizer_matches_submitted_exclusion_change(self):
        future = future_range(
            301, 308, market_by_step={301: [["SELL", "FERTILIZER", 3]]}
        )
        enabled = R04MarketMicrostackCurrentABI(
            sale_window=True, sale_fertilizer=True
        )
        disabled = R04MarketMicrostackCurrentABI(
            sale_window=True, sale_fertilizer=False
        )
        args = dict(
            observation=observation(300),
            configuration=None,
            selected_action=action(),
            post_unit_shed=shed(FERTILIZER=3),
            future_actions=future,
            queued_commands=[],
        )
        yes, _ = enabled.sale_window_transform(**args)
        no, _ = disabled.sale_window_transform(**args)
        self.assertEqual(yes["market"], [["SELL", "FERTILIZER", 3]])
        self.assertEqual(no["market"], [])

    def test_current_sell_and_queued_pickup_block_reservation(self):
        future = future_range(
            301, 308, market_by_step={301: [["SELL", "CARROT", 4]]}
        )
        component = R04MarketMicrostackCurrentABI(sale_window=True)
        current, _ = component.sale_window_transform(
            observation(300),
            None,
            action(market=[["SELL", "CARROT", 1]]),
            post_unit_shed=shed(CARROT=4),
            future_actions=future,
            queued_commands=[],
        )
        self.assertEqual(current["market"], [["SELL", "CARROT", 1]])

        component = R04MarketMicrostackCurrentABI(sale_window=True)
        queued, _ = component.sale_window_transform(
            observation(300),
            None,
            action(),
            post_unit_shed=shed(CARROT=4),
            future_actions=future,
            queued_commands=[["PICKUP", "CARROT"]],
        )
        self.assertEqual(queued["market"], [])

    def test_future_pickup_stops_after_earlier_due_reservation(self):
        future = future_range(
            301,
            308,
            market_by_step={
                301: [["SELL", "CARROT", 2]],
                302: [["SELL", "CARROT", 2]],
            },
            farmer_by_step={302: ["PICKUP", "CARROT"]},
        )
        component = R04MarketMicrostackCurrentABI(sale_window=True)
        result, report = component.sale_window_transform(
            observation(300),
            None,
            action(),
            post_unit_shed=shed(CARROT=4),
            future_actions=future,
            queued_commands=[],
        )
        self.assertEqual(result["market"], [["SELL", "CARROT", 2]])
        self.assertEqual(report["debts_after"], {301: {"CARROT": 2}})

    def test_animal_place_uncertainty_is_identity(self):
        future = future_range(
            301, 308, market_by_step={301: [["SELL", "CARROT", 4]]}
        )
        component = R04MarketMicrostackCurrentABI(sale_window=True)
        selected = action(farmer=["PLACE", "SHEEP"])
        result, report = component.sale_window_transform(
            observation(300, inventories=[{"SHEEP": 1}]),
            None,
            selected,
            post_unit_shed=shed(CARROT=4),
            future_actions=future,
            queued_commands=[],
        )
        self.assertEqual(result, selected)
        self.assertEqual(report["reason"], "animal_place_uncertain")

    def test_native_pre288_advance_and_due_settlement(self):
        component = R04MarketMicrostackCurrentABI(sale_window=True)
        first, report = component.sale_window_transform(
            observation(200),
            None,
            action(),
            post_unit_shed=shed(CARROT=4),
            future_actions={201: action(market=[["SELL", "CARROT", 4]])},
        )
        self.assertEqual(first["market"], [["SELL", "CARROT", 4]])
        self.assertEqual(report["native_due_step"], 201)

        second, report = component.sale_window_transform(
            observation(201),
            None,
            action(market=[["SELL", "CARROT", 4]]),
            post_unit_shed=shed(CARROT=4),
            future_actions={202: action()},
        )
        self.assertEqual(second["market"], [])
        self.assertTrue(report["sales_first_changed"])
        self.assertEqual(report["native_due_step"], -1)

    def _drive_opening(self, component, *, same_rival):
        for step in range(144):
            component.sale_window_transform(
                observation(step, same_rival=same_rival),
                None,
                action(),
                post_unit_shed=shed(),
                future_actions={step + 1: action()},
            )

    def test_l3_suppresses_only_certified_off_tape_rival(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True, no_late_sale_advance=True
        )
        self._drive_opening(component, same_rival=False)
        future = future_range(
            649, 656, market_by_step={649: [["SELL", "CARROT", 3]]}
        )
        result, report = component.sale_window_transform(
            observation(648, same_rival=False),
            None,
            action(),
            post_unit_shed=shed(CARROT=3),
            future_actions=future,
            queued_commands=[],
        )
        self.assertEqual(result["market"], [])
        self.assertFalse(report["on_tape"])
        self.assertTrue(report["l3_suppressed"])

    def test_l3_incomplete_opening_fails_closed_to_h8(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True, no_late_sale_advance=True
        )
        future = future_range(
            649, 656, market_by_step={649: [["SELL", "CARROT", 3]]}
        )
        result, report = component.sale_window_transform(
            observation(648, same_rival=False),
            None,
            action(),
            post_unit_shed=shed(CARROT=3),
            future_actions=future,
            queued_commands=[],
        )
        self.assertEqual(result["market"], [["SELL", "CARROT", 3]])
        self.assertTrue(report["on_tape"])
        self.assertFalse(report["l3_suppressed"])

    def test_l3_on_tape_rival_keeps_h8_active(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True, no_late_sale_advance=True
        )
        self._drive_opening(component, same_rival=True)
        future = future_range(
            649, 656, market_by_step={649: [["SELL", "CARROT", 3]]}
        )
        result, report = component.sale_window_transform(
            observation(648, same_rival=True),
            None,
            action(),
            post_unit_shed=shed(CARROT=3),
            future_actions=future,
            queued_commands=[],
        )
        self.assertEqual(result["market"], [["SELL", "CARROT", 3]])
        self.assertTrue(report["on_tape"])
        self.assertFalse(report["l3_suppressed"])

    def test_prior_debt_settles_even_when_l3_suppresses_new_reservation(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True, no_late_sale_advance=True
        )
        self._drive_opening(component, same_rival=False)
        future = future_range(
            648, 655, market_by_step={648: [["SELL", "CARROT", 3]]}
        )
        first, report = component.sale_window_transform(
            observation(647, same_rival=False),
            None,
            action(),
            post_unit_shed=shed(CARROT=3),
            future_actions=future,
            queued_commands=[],
        )
        self.assertEqual(first["market"], [["SELL", "CARROT", 3]])
        self.assertEqual(report["debts_after"], {648: {"CARROT": 3}})

        second, report = component.sale_window_transform(
            observation(648, same_rival=False),
            None,
            action(market=[["SELL", "CARROT", 3]]),
            post_unit_shed=shed(CARROT=3),
        )
        self.assertEqual(second["market"], [])
        self.assertTrue(report["l3_suppressed"])
        self.assertEqual(component.reservation_debts(0), {})

    def test_shared_debt_seam_accepts_h4_updated_snapshot(self):
        component = R04MarketMicrostackCurrentABI(sale_window=True)
        future = future_range(
            301, 308, market_by_step={301: [["SELL", "CARROT", 2]]}
        )
        component.sale_window_transform(
            observation(300),
            None,
            action(),
            post_unit_shed=shed(CARROT=2),
            future_actions=future,
            queued_commands=[],
        )
        debts = component.reservation_debts(0)
        debts[302] = {"STRAWBERRY": 1}
        component.replace_reservation_debts(0, debts)
        self.assertEqual(
            component.reservation_debts(0),
            {301: {"CARROT": 2}, 302: {"STRAWBERRY": 1}},
        )
        debts[302]["STRAWBERRY"] = 99
        self.assertEqual(component.reservation_debts(0)[302]["STRAWBERRY"], 1)

    def test_v224_sales_first_exact_positive_row_order(self):
        component = R04MarketMicrostackCurrentABI(sale_window=True)
        selected = action(
            market=[
                ["HIRE"],
                ["BUY_SEED", "WHEAT", 1],
                ["SELL", "CARROT", 1],
                ["BUY_PRODUCT", "MILK", 1],
                ["SELL", "MILK", 1],
            ]
        )
        result, report = component.sale_window_transform(
            observation(300),
            None,
            selected,
            post_unit_shed=shed(),
        )
        self.assertEqual(
            result["market"],
            [
                ["SELL", "CARROT", 1],
                ["HIRE"],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_PRODUCT", "MILK", 1],
                ["SELL", "MILK", 1],
            ],
        )
        self.assertTrue(report["sales_first_changed"])

    def test_preexisting_dead_row_fails_closed_not_compacted(self):
        component = R04MarketMicrostackCurrentABI(sale_window=True)
        selected = action(market=[["SELL", "CARROT", 0]])
        result, report = component.sale_window_transform(
            observation(300),
            None,
            selected,
            post_unit_shed=shed(CARROT=3),
        )
        self.assertEqual(result, selected)
        self.assertTrue(report["reason"].startswith("fail_closed:"))

    def test_evening_flush_prepends_exact_remaining_steep_goods(self):
        component = R04MarketMicrostackCurrentABI(evening_flush=True)
        selected = action(market=[["SELL", "WOOL", 2]])
        result, report = component.evening_flush_transform(
            observation(45),
            None,
            selected,
            post_unit_shed=shed(WOOL=10, MILK=5),
        )
        self.assertEqual(
            result["market"],
            [
                ["SELL", "WOOL", 8],
                ["SELL", "MILK", 5],
                ["SELL", "WOOL", 2],
            ],
        )
        self.assertEqual(report["reason"], "evening_flush")

    def test_evening_flush_window_and_capacity_are_bounded(self):
        component = R04MarketMicrostackCurrentABI(evening_flush=True)
        selected = action()
        outside, _ = component.evening_flush_transform(
            observation(44),
            None,
            selected,
            post_unit_shed=shed(WOOL=10),
        )
        self.assertEqual(outside, selected)

        full = action(market=[["HIRE"] for _ in range(10)])
        bounded, report = component.evening_flush_transform(
            observation(45),
            None,
            full,
            post_unit_shed=shed(WOOL=10),
        )
        self.assertEqual(bounded, full)
        self.assertEqual(report["reason"], "no_flush_room_or_stock")

    def test_stage_separation_leaves_h4_row_shed_slot_explicit(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True, evening_flush=True
        )
        pre, _ = component.sale_window_transform(
            observation(45),
            None,
            action(),
            post_unit_shed=shed(WOOL=5),
            future_actions={46: action()},
        )
        self.assertEqual(pre["market"], [])
        post, _ = component.evening_flush_transform(
            observation(45),
            None,
            pre,
            post_unit_shed=shed(WOOL=5),
        )
        self.assertEqual(post["market"], [["SELL", "WOOL", 5]])


if __name__ == "__main__":
    unittest.main()
