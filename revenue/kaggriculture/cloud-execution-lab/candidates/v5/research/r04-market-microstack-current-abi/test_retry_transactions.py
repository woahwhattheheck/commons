# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

from market_microstack_current_safe import R04MarketMicrostackCurrentABI
from test_market_microstack_current import action, future_range, observation, shed


class RetryTransactionTests(unittest.TestCase):
    def _drive_off_tape_opening(self, component):
        for step in range(144):
            component.sale_window_transform(
                observation(step, same_rival=False),
                None,
                action(),
                post_unit_shed=shed(),
                future_actions={step + 1: action()},
            )

    def test_off_tape_l3_exact_retry_stays_suppressed(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True,
            no_late_sale_advance=True,
        )
        self._drive_off_tape_opening(component)
        future = future_range(
            649,
            656,
            market_by_step={649: [["SELL", "CARROT", 3]]},
        )
        kwargs = dict(
            observation=observation(648, same_rival=False),
            configuration=None,
            selected_action=action(),
            post_unit_shed=shed(CARROT=3),
            future_actions=future,
            queued_commands=[],
        )
        first, first_report = component.sale_window_transform(**kwargs)
        second, second_report = component.sale_window_transform(**copy.deepcopy(kwargs))
        self.assertEqual(first, second)
        self.assertEqual(first_report, second_report)
        self.assertEqual(first["market"], [])
        self.assertFalse(second_report["on_tape"])
        self.assertTrue(second_report["l3_suppressed"])

    def test_off_tape_l3_changed_same_step_recomputes_without_gate_reset(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True,
            no_late_sale_advance=True,
        )
        self._drive_off_tape_opening(component)
        first_future = future_range(
            649,
            656,
            market_by_step={649: [["SELL", "CARROT", 3]]},
        )
        first, first_report = component.sale_window_transform(
            observation(648, same_rival=False),
            None,
            action(),
            post_unit_shed=shed(CARROT=3),
            future_actions=first_future,
            queued_commands=[],
        )
        self.assertEqual(first["market"], [])
        self.assertTrue(first_report["l3_suppressed"])

        changed_future = future_range(
            649,
            656,
            market_by_step={649: [["SELL", "CARROT", 7]]},
        )
        changed, changed_report = component.sale_window_transform(
            observation(648, same_rival=False),
            None,
            action(),
            post_unit_shed=shed(CARROT=7),
            future_actions=changed_future,
            queued_commands=[],
        )
        self.assertEqual(changed["market"], [])
        self.assertFalse(changed_report["on_tape"])
        self.assertTrue(changed_report["l3_suppressed"])

    def test_due_debt_settlement_exact_retry_preserves_future_debt_once(self):
        component = R04MarketMicrostackCurrentABI(sale_window=True)
        component.replace_reservation_debts(
            0,
            {
                300: {"CARROT": 2},
                302: {"MILK": 1},
            },
        )
        kwargs = dict(
            observation=observation(300),
            configuration=None,
            selected_action=action(market=[["SELL", "CARROT", 2]]),
            post_unit_shed=shed(CARROT=2),
        )
        first, first_report = component.sale_window_transform(**kwargs)
        self.assertEqual(first["market"], [])
        self.assertEqual(component.reservation_debts(0), {302: {"MILK": 1}})

        second, second_report = component.sale_window_transform(**copy.deepcopy(kwargs))
        self.assertEqual(second, first)
        self.assertEqual(second_report, first_report)
        self.assertEqual(component.reservation_debts(0), {302: {"MILK": 1}})

        due, _ = component.sale_window_transform(
            observation(302),
            None,
            action(market=[["SELL", "MILK", 1]]),
            post_unit_shed=shed(MILK=1),
        )
        self.assertEqual(due["market"], [])
        self.assertEqual(component.reservation_debts(0), {})

    def test_h4_shared_debt_written_after_stage_survives_exact_retry(self):
        component = R04MarketMicrostackCurrentABI(sale_window=True)
        future = future_range(
            301,
            308,
            market_by_step={301: [["SELL", "CARROT", 2]]},
        )
        kwargs = dict(
            observation=observation(300),
            configuration=None,
            selected_action=action(),
            post_unit_shed=shed(CARROT=2),
            future_actions=future,
            queued_commands=[],
        )
        first, _ = component.sale_window_transform(**kwargs)
        self.assertEqual(first["market"], [["SELL", "CARROT", 2]])

        shared = component.reservation_debts(0)
        shared[305] = {"STRAWBERRY": 2}
        component.replace_reservation_debts(0, shared)

        retry, _ = component.sale_window_transform(**copy.deepcopy(kwargs))
        self.assertEqual(retry, first)
        self.assertEqual(
            component.reservation_debts(0),
            {
                301: {"CARROT": 2},
                305: {"STRAWBERRY": 2},
            },
        )

    def test_changed_same_step_discards_prior_attempt_poststate_not_prestep_authority(self):
        component = R04MarketMicrostackCurrentABI(sale_window=True)
        component.replace_reservation_debts(0, {302: {"MILK": 1}})

        first_future = future_range(
            301,
            308,
            market_by_step={301: [["SELL", "CARROT", 2]]},
        )
        first, _ = component.sale_window_transform(
            observation(300),
            None,
            action(),
            post_unit_shed=shed(CARROT=2),
            future_actions=first_future,
            queued_commands=[],
        )
        self.assertEqual(first["market"], [["SELL", "CARROT", 2]])
        shared = component.reservation_debts(0)
        shared[305] = {"STRAWBERRY": 2}
        component.replace_reservation_debts(0, shared)
        self.assertEqual(
            component.reservation_debts(0),
            {
                301: {"CARROT": 2},
                302: {"MILK": 1},
                305: {"STRAWBERRY": 2},
            },
        )

        changed_future = future_range(301, 308)
        changed, _ = component.sale_window_transform(
            observation(300),
            None,
            action(),
            post_unit_shed=shed(),
            future_actions=changed_future,
            queued_commands=[],
        )
        self.assertEqual(changed["market"], [])
        self.assertEqual(component.reservation_debts(0), {302: {"MILK": 1}})

    def test_true_rewind_is_strictly_earlier_not_same_step(self):
        component = R04MarketMicrostackCurrentABI(sale_window=True)
        first, _ = component.sale_window_transform(
            observation(300),
            None,
            action(),
            post_unit_shed=shed(),
        )
        retry, _ = component.sale_window_transform(
            observation(300),
            None,
            action(),
            post_unit_shed=shed(),
        )
        self.assertEqual(retry, first)

        rewound, report = component.sale_window_transform(
            observation(10),
            None,
            action(),
            post_unit_shed=shed(),
            future_actions={11: action()},
        )
        self.assertEqual(rewound["market"], [])
        self.assertTrue(report["on_tape"])


if __name__ == "__main__":
    unittest.main()
