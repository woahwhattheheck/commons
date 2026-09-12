# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

from market_microstack_current import ADVANCE_START, L3_THRESHOLD, SALE_HORIZON
from market_microstack_current_safe import R04MarketMicrostackCurrentABI
from test_support import action, authority, future_range, observation, shed


class MarketMicrostackTests(unittest.TestCase):
    def test_submitted_constants_are_fixed(self):
        self.assertEqual(ADVANCE_START, 288)
        self.assertEqual(SALE_HORIZON, 8)
        self.assertEqual(L3_THRESHOLD, 648)

    def test_flags_require_exact_bool(self):
        with self.assertRaises(TypeError):
            R04MarketMicrostackCurrentABI(sale_window=1)

    def test_default_off_is_exact_identity_without_route_authority(self):
        component = R04MarketMicrostackCurrentABI()
        selected = action(market=[["SELL", "CARROT", 2]])
        before = copy.deepcopy(selected)
        result, report = component.sale_window_transform(
            observation(300), None, selected, post_unit_shed=shed(CARROT=2)
        )
        self.assertEqual(result, before)
        self.assertEqual(selected, before)
        self.assertEqual(report["reason"], "disabled")

    def test_enabled_stage_requires_canonical_route_authority(self):
        component = R04MarketMicrostackCurrentABI(sale_window=True)
        selected = action()
        result, report = component.sale_window_transform(
            observation(300), None, selected, post_unit_shed=shed(CARROT=4)
        )
        self.assertEqual(result, selected)
        self.assertFalse(report["authorizing"])
        self.assertEqual(
            report["reason"], "fail_closed:canonical_route_authority_required"
        )

    def test_e184_h8_reserves_authenticated_future_sales_and_debt(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True,
            sale_fertilizer=True,
            no_late_sale_advance=True,
        )
        obs = observation(300)
        future = future_range(
            301,
            308,
            market_by_step={
                301: [["SELL", "CARROT", 2]],
                302: [["SELL", "CARROT", 3]],
            },
        )
        result, report = component.sale_window_transform(
            obs,
            None,
            action(),
            post_unit_shed=shed(CARROT=4),
            route_authority=authority(obs, future),
        )
        self.assertEqual(result["market"], [["SELL", "CARROT", 4]])
        self.assertEqual(
            report["debts_after"],
            {301: {"CARROT": 2}, 302: {"CARROT": 2}},
        )
        self.assertTrue(report["authorizing"])
        self.assertTrue(report["route_authority_sha256"])
        self.assertTrue(report["window_sha256"])

    def test_sale_fertilizer_matches_submitted_exclusion_change(self):
        obs = observation(300)
        future = future_range(
            301, 308, market_by_step={301: [["SELL", "FERTILIZER", 3]]}
        )
        enabled = R04MarketMicrostackCurrentABI(
            sale_window=True, sale_fertilizer=True
        )
        disabled = R04MarketMicrostackCurrentABI(
            sale_window=True, sale_fertilizer=False
        )
        yes, _ = enabled.sale_window_transform(
            obs,
            None,
            action(),
            post_unit_shed=shed(FERTILIZER=3),
            route_authority=authority(obs, future),
        )
        no, _ = disabled.sale_window_transform(
            obs,
            None,
            action(),
            post_unit_shed=shed(FERTILIZER=3),
            route_authority=authority(obs, future),
        )
        self.assertEqual(yes["market"], [["SELL", "FERTILIZER", 3]])
        self.assertEqual(no["market"], [])

    def test_current_sell_and_current_pickup_block_reservation(self):
        obs = observation(300)
        future = future_range(
            301, 308, market_by_step={301: [["SELL", "CARROT", 4]]}
        )
        component = R04MarketMicrostackCurrentABI(sale_window=True)
        current, _ = component.sale_window_transform(
            obs,
            None,
            action(market=[["SELL", "CARROT", 1]]),
            post_unit_shed=shed(CARROT=4),
            route_authority=authority(obs, future),
        )
        self.assertEqual(current["market"], [["SELL", "CARROT", 1]])

        pickup_component = R04MarketMicrostackCurrentABI(sale_window=True)
        pickup, _ = pickup_component.sale_window_transform(
            obs,
            None,
            action(farmer=["PICKUP", "CARROT"]),
            post_unit_shed=shed(CARROT=4),
            route_authority=authority(obs, future),
        )
        self.assertEqual(pickup["market"], [])

    def test_future_pickup_stops_after_earlier_due_reservation(self):
        obs = observation(300)
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
            obs,
            None,
            action(),
            post_unit_shed=shed(CARROT=4),
            route_authority=authority(obs, future),
        )
        self.assertEqual(result["market"], [["SELL", "CARROT", 2]])
        self.assertEqual(report["debts_after"], {301: {"CARROT": 2}})

    def test_animal_place_uncertainty_is_identity(self):
        obs = observation(300, inventories=[{"SHEEP": 1}])
        future = future_range(
            301, 308, market_by_step={301: [["SELL", "CARROT", 4]]}
        )
        component = R04MarketMicrostackCurrentABI(sale_window=True)
        selected = action(farmer=["PLACE", "SHEEP"])
        result, report = component.sale_window_transform(
            obs,
            None,
            selected,
            post_unit_shed=shed(CARROT=4),
            route_authority=authority(obs, future),
        )
        self.assertEqual(result, selected)
        self.assertEqual(report["reason"], "animal_place_uncertain")

    def test_native_pre288_advance_and_due_settlement(self):
        component = R04MarketMicrostackCurrentABI(sale_window=True)
        obs200 = observation(200)
        first_future = {201: action(market=[["SELL", "CARROT", 4]])}
        first, report = component.sale_window_transform(
            obs200,
            None,
            action(),
            post_unit_shed=shed(CARROT=4),
            route_authority=authority(obs200, first_future),
        )
        self.assertEqual(first["market"], [["SELL", "CARROT", 4]])
        self.assertEqual(report["native_due_step"], 201)

        obs201 = observation(201)
        second, report = component.sale_window_transform(
            obs201,
            None,
            action(market=[["SELL", "CARROT", 4]]),
            post_unit_shed=shed(CARROT=4),
            route_authority=authority(obs201, {202: action()}),
        )
        self.assertEqual(second["market"], [])
        self.assertTrue(report["sales_first_changed"])
        self.assertEqual(report["native_due_step"], -1)

    def _drive_opening(self, component, *, same_rival):
        for step in range(144):
            obs = observation(step, same_rival=same_rival)
            component.sale_window_transform(
                obs,
                None,
                action(),
                post_unit_shed=shed(),
                route_authority=authority(obs),
            )

    def test_l3_suppresses_only_certified_off_tape_rival(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True, no_late_sale_advance=True
        )
        self._drive_opening(component, same_rival=False)
        obs = observation(648, same_rival=False)
        future = future_range(
            649, 656, market_by_step={649: [["SELL", "CARROT", 3]]}
        )
        result, report = component.sale_window_transform(
            obs,
            None,
            action(),
            post_unit_shed=shed(CARROT=3),
            route_authority=authority(obs, future),
        )
        self.assertEqual(result["market"], [])
        self.assertFalse(report["on_tape"])
        self.assertTrue(report["l3_suppressed"])

    def test_l3_incomplete_opening_fails_closed_to_h8(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True, no_late_sale_advance=True
        )
        obs = observation(648, same_rival=False)
        future = future_range(
            649, 656, market_by_step={649: [["SELL", "CARROT", 3]]}
        )
        result, report = component.sale_window_transform(
            obs,
            None,
            action(),
            post_unit_shed=shed(CARROT=3),
            route_authority=authority(obs, future),
        )
        self.assertEqual(result["market"], [["SELL", "CARROT", 3]])
        self.assertTrue(report["on_tape"])
        self.assertFalse(report["l3_suppressed"])

    def test_l3_on_tape_rival_keeps_h8_active(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True, no_late_sale_advance=True
        )
        self._drive_opening(component, same_rival=True)
        obs = observation(648, same_rival=True)
        future = future_range(
            649, 656, market_by_step={649: [["SELL", "CARROT", 3]]}
        )
        result, report = component.sale_window_transform(
            obs,
            None,
            action(),
            post_unit_shed=shed(CARROT=3),
            route_authority=authority(obs, future),
        )
        self.assertEqual(result["market"], [["SELL", "CARROT", 3]])
        self.assertTrue(report["on_tape"])
        self.assertFalse(report["l3_suppressed"])

    def test_existing_shared_debt_settles_when_l3_suppresses_new_reservation(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True, no_late_sale_advance=True
        )
        self._drive_opening(component, same_rival=False)
        component.replace_reservation_debts(0, {648: {"CARROT": 3}})
        obs = observation(648, same_rival=False)
        result, report = component.sale_window_transform(
            obs,
            None,
            action(market=[["SELL", "CARROT", 3]]),
            post_unit_shed=shed(CARROT=3),
            route_authority=authority(obs),
        )
        self.assertEqual(result["market"], [])
        self.assertTrue(report["l3_suppressed"])
        self.assertEqual(component.reservation_debts(0), {})

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
        obs = observation(300)
        result, report = component.sale_window_transform(
            obs,
            None,
            selected,
            post_unit_shed=shed(),
            route_authority=authority(obs),
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
        obs = observation(300)
        result, report = component.sale_window_transform(
            obs,
            None,
            selected,
            post_unit_shed=shed(CARROT=3),
            route_authority=authority(obs),
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
            observation(44), None, selected, post_unit_shed=shed(WOOL=10)
        )
        self.assertEqual(outside, selected)
        full = action(market=[["HIRE"] for _ in range(10)])
        bounded, report = component.evening_flush_transform(
            observation(45), None, full, post_unit_shed=shed(WOOL=10)
        )
        self.assertEqual(bounded, full)
        self.assertEqual(report["reason"], "no_flush_room_or_stock")


if __name__ == "__main__":
    unittest.main()
