# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

from market_microstack_current_safe import R04MarketMicrostackCurrentABI
from test_support import action, authority, future_range, observation, shed


class RetryTransactionTests(unittest.TestCase):
    def _drive_off_tape_opening(self, component):
        for step in range(144):
            obs = observation(step, same_rival=False)
            component.sale_window_transform(
                obs,
                None,
                action(),
                post_unit_shed=shed(),
                route_authority=authority(obs),
            )

    def test_off_tape_l3_exact_retry_stays_suppressed(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True, no_late_sale_advance=True
        )
        self._drive_off_tape_opening(component)
        obs = observation(648, same_rival=False)
        future = future_range(
            649, 656, market_by_step={649: [["SELL", "CARROT", 3]]}
        )
        route = authority(obs, future)
        first, first_report = component.sale_window_transform(
            obs,
            None,
            action(),
            post_unit_shed=shed(CARROT=3),
            route_authority=route,
        )
        second, second_report = component.sale_window_transform(
            copy.deepcopy(obs),
            None,
            action(),
            post_unit_shed=shed(CARROT=3),
            route_authority=route,
        )
        self.assertEqual(first, second)
        self.assertEqual(first_report, second_report)
        self.assertEqual(first["market"], [])
        self.assertFalse(second_report["on_tape"])
        self.assertTrue(second_report["l3_suppressed"])

    def test_changed_same_step_route_digest_recomputes_without_gate_reset(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True, no_late_sale_advance=True
        )
        self._drive_off_tape_opening(component)
        obs = observation(648, same_rival=False)
        first_future = future_range(
            649, 656, market_by_step={649: [["SELL", "CARROT", 3]]}
        )
        first, report = component.sale_window_transform(
            obs,
            None,
            action(),
            post_unit_shed=shed(CARROT=3),
            route_authority=authority(obs, first_future),
        )
        self.assertEqual(first["market"], [])
        self.assertTrue(report["l3_suppressed"])

        changed_future = future_range(
            649, 656, market_by_step={649: [["SELL", "CARROT", 7]]}
        )
        changed, changed_report = component.sale_window_transform(
            obs,
            None,
            action(),
            post_unit_shed=shed(CARROT=7),
            route_authority=authority(obs, changed_future),
        )
        self.assertEqual(changed["market"], [])
        self.assertFalse(changed_report["on_tape"])
        self.assertTrue(changed_report["l3_suppressed"])
        self.assertNotEqual(
            report["route_authority_sha256"],
            changed_report["route_authority_sha256"],
        )

    def test_due_debt_settlement_exact_retry_preserves_future_debt_once(self):
        component = R04MarketMicrostackCurrentABI(sale_window=True)
        component.replace_reservation_debts(
            0, {300: {"CARROT": 2}, 302: {"MILK": 1}}
        )
        obs300 = observation(300)
        route300 = authority(obs300)
        first, first_report = component.sale_window_transform(
            obs300,
            None,
            action(market=[["SELL", "CARROT", 2]]),
            post_unit_shed=shed(CARROT=2),
            route_authority=route300,
        )
        self.assertEqual(first["market"], [])
        self.assertEqual(component.reservation_debts(0), {302: {"MILK": 1}})

        second, second_report = component.sale_window_transform(
            copy.deepcopy(obs300),
            None,
            action(market=[["SELL", "CARROT", 2]]),
            post_unit_shed=shed(CARROT=2),
            route_authority=route300,
        )
        self.assertEqual(second, first)
        self.assertEqual(second_report, first_report)
        self.assertEqual(component.reservation_debts(0), {302: {"MILK": 1}})

        obs302 = observation(302)
        due, _ = component.sale_window_transform(
            obs302,
            None,
            action(market=[["SELL", "MILK", 1]]),
            post_unit_shed=shed(MILK=1),
            route_authority=authority(obs302),
        )
        self.assertEqual(due["market"], [])
        self.assertEqual(component.reservation_debts(0), {})

    def test_h4_shared_debt_written_after_stage_survives_exact_retry(self):
        component = R04MarketMicrostackCurrentABI(sale_window=True)
        obs = observation(300)
        future = future_range(
            301, 308, market_by_step={301: [["SELL", "CARROT", 2]]}
        )
        route = authority(obs, future)
        first, _ = component.sale_window_transform(
            obs,
            None,
            action(),
            post_unit_shed=shed(CARROT=2),
            route_authority=route,
        )
        self.assertEqual(first["market"], [["SELL", "CARROT", 2]])
        shared = component.reservation_debts(0)
        shared[305] = {"STRAWBERRY": 2}
        component.replace_reservation_debts(0, shared)

        retry, _ = component.sale_window_transform(
            copy.deepcopy(obs),
            None,
            action(),
            post_unit_shed=shed(CARROT=2),
            route_authority=route,
        )
        self.assertEqual(retry, first)
        self.assertEqual(
            component.reservation_debts(0),
            {301: {"CARROT": 2}, 305: {"STRAWBERRY": 2}},
        )

    def test_changed_same_step_authority_discards_prior_attempt_poststate(self):
        component = R04MarketMicrostackCurrentABI(sale_window=True)
        component.replace_reservation_debts(0, {302: {"MILK": 1}})
        obs = observation(300)
        first_future = future_range(
            301, 308, market_by_step={301: [["SELL", "CARROT", 2]]}
        )
        first, _ = component.sale_window_transform(
            obs,
            None,
            action(),
            post_unit_shed=shed(CARROT=2),
            route_authority=authority(obs, first_future),
        )
        self.assertEqual(first["market"], [["SELL", "CARROT", 2]])
        shared = component.reservation_debts(0)
        shared[305] = {"STRAWBERRY": 2}
        component.replace_reservation_debts(0, shared)

        changed, _ = component.sale_window_transform(
            obs,
            None,
            action(),
            post_unit_shed=shed(),
            route_authority=authority(obs),
        )
        self.assertEqual(changed["market"], [])
        self.assertEqual(component.reservation_debts(0), {302: {"MILK": 1}})

    def test_true_rewind_is_strictly_earlier_not_same_step(self):
        component = R04MarketMicrostackCurrentABI(sale_window=True)
        obs300 = observation(300)
        route300 = authority(obs300)
        first, _ = component.sale_window_transform(
            obs300,
            None,
            action(),
            post_unit_shed=shed(),
            route_authority=route300,
        )
        retry, _ = component.sale_window_transform(
            copy.deepcopy(obs300),
            None,
            action(),
            post_unit_shed=shed(),
            route_authority=route300,
        )
        self.assertEqual(retry, first)

        obs10 = observation(10)
        rewound, report = component.sale_window_transform(
            obs10,
            None,
            action(),
            post_unit_shed=shed(),
            route_authority=authority(obs10),
        )
        self.assertEqual(rewound["market"], [])
        self.assertTrue(report["on_tape"])


if __name__ == "__main__":
    unittest.main()
