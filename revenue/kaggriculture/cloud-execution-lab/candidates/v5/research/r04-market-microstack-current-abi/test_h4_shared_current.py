# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
from pathlib import Path
import subprocess
import unittest

from market_microstack_current_safe import (
    H4_DONOR_BLOB,
    H4_DONOR_COMMIT,
    H4_DONOR_PATH,
    R04MarketMicrostackCurrentABI,
)
from test_market_microstack_current import action, future_range, observation, shed


class H4SharedLedgerTests(unittest.TestCase):
    def _stage(self, component, *, step=300, selected=None, stock=None, future=None,
               queued=None, obs=None):
        if selected is None:
            selected = action(market=[["SELL", "STRAWBERRY", 1]])
        if stock is None:
            stock = shed(STRAWBERRY=4)
        if future is None:
            future = future_range(
                step + 1,
                min(718, step + 8, (step // 72 + 1) * 72 - 1),
                market_by_step={step + 1: [["SELL", "STRAWBERRY", 3]]},
            )
        if queued is None:
            queued = []
        if obs is None:
            obs = observation(step)
        pre, sale_report = component.sale_window_transform(
            obs,
            None,
            selected,
            post_unit_shed=stock,
            future_actions=future,
            queued_commands=queued,
        )
        post, h4_report = component.strawberry_topup_transform(
            obs,
            None,
            pre,
            post_unit_shed=stock,
            future_actions=future,
            queued_commands=queued,
        )
        return pre, sale_report, post, h4_report

    def test_exact_submitted_h4_blob_is_repository_authority(self):
        root = Path(__file__).resolve().parent
        blob = subprocess.check_output(
            ["git", "rev-parse", f"{H4_DONOR_COMMIT}:{H4_DONOR_PATH}"],
            cwd=root,
            text=True,
        ).strip()
        self.assertEqual(blob, H4_DONOR_BLOB)

    def test_h4_requires_literal_bool(self):
        with self.assertRaises(TypeError):
            R04MarketMicrostackCurrentABI(strawberry_topup=1)

    def test_h4_requires_same_step_sale_window_authority(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True,
            strawberry_topup=True,
        )
        selected = action(market=[["SELL", "STRAWBERRY", 1]])
        result, report = component.strawberry_topup_transform(
            observation(300),
            None,
            selected,
            post_unit_shed=shed(STRAWBERRY=4),
            future_actions=future_range(
                301, 308, market_by_step={301: [["SELL", "STRAWBERRY", 3]]}
            ),
            queued_commands=[],
        )
        self.assertEqual(result, selected)
        self.assertEqual(report["reason"], "requires_same_step_sale_window_stage")

    def test_existing_strawberry_row_tops_up_from_authored_future_sale(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True,
            strawberry_topup=True,
        )
        pre, _, post, report = self._stage(component)
        self.assertEqual(pre["market"], [["SELL", "STRAWBERRY", 1]])
        self.assertEqual(post["market"], [["SELL", "STRAWBERRY", 4]])
        self.assertTrue(report["changed"])
        self.assertEqual(report["reservations"], ((301, 3),))
        self.assertEqual(
            component.reservation_debts(0),
            {301: {"STRAWBERRY": 3}},
        )

    def test_h4_exact_retry_is_idempotent_and_does_not_double_reserve(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True,
            strawberry_topup=True,
        )
        selected = action(market=[["SELL", "STRAWBERRY", 1]])
        stock = shed(STRAWBERRY=4)
        future = future_range(
            301, 308, market_by_step={301: [["SELL", "STRAWBERRY", 3]]}
        )
        pre, _ = component.sale_window_transform(
            observation(300),
            None,
            selected,
            post_unit_shed=stock,
            future_actions=future,
            queued_commands=[],
        )
        first, first_report = component.strawberry_topup_transform(
            observation(300),
            None,
            pre,
            post_unit_shed=stock,
            future_actions=future,
            queued_commands=[],
        )
        second, second_report = component.strawberry_topup_transform(
            observation(300),
            None,
            copy.deepcopy(pre),
            post_unit_shed=copy.deepcopy(stock),
            future_actions=copy.deepcopy(future),
            queued_commands=[],
        )
        self.assertEqual(second, first)
        self.assertEqual(second_report, first_report)
        self.assertEqual(
            component.reservation_debts(0),
            {301: {"STRAWBERRY": 3}},
        )

    def test_h4_due_debt_is_repaid_by_sale_window_before_fresh_h4(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True,
            strawberry_topup=True,
        )
        self._stage(component)
        self.assertEqual(
            component.reservation_debts(0),
            {301: {"STRAWBERRY": 3}},
        )

        future = future_range(302, 309)
        due, sale_report = component.sale_window_transform(
            observation(301),
            None,
            action(market=[["SELL", "STRAWBERRY", 3]]),
            post_unit_shed=shed(STRAWBERRY=3),
            future_actions=future,
            queued_commands=[],
        )
        self.assertEqual(due["market"], [])
        self.assertEqual(component.reservation_debts(0), {})
        self.assertTrue(sale_report["sales_first_changed"])

        h4, h4_report = component.strawberry_topup_transform(
            observation(301),
            None,
            due,
            post_unit_shed=shed(STRAWBERRY=3),
            future_actions=future,
            queued_commands=[],
        )
        self.assertEqual(h4, due)
        self.assertEqual(h4_report["reason"], "requires_one_current_sell")
        self.assertEqual(component.reservation_debts(0), {})

    def test_h4_cannot_create_a_new_strawberry_row(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True,
            strawberry_topup=True,
        )
        future = future_range(
            301, 308, market_by_step={301: [["SELL", "STRAWBERRY", 3]]}
        )
        pre, _ = component.sale_window_transform(
            observation(300),
            None,
            action(),
            post_unit_shed=shed(STRAWBERRY=3),
            future_actions=future,
            queued_commands=[],
        )
        # H8 itself may create a row; use a current STRAWBERRY pickup blocker so
        # the upstream stage is identity and H4 sees no existing SELL row.
        blocked_action = action(farmer=["PICKUP", "STRAWBERRY"])
        component2 = R04MarketMicrostackCurrentABI(
            sale_window=True,
            strawberry_topup=True,
        )
        pre, _ = component2.sale_window_transform(
            observation(300),
            None,
            blocked_action,
            post_unit_shed=shed(STRAWBERRY=3),
            future_actions=future,
            queued_commands=[],
        )
        post, report = component2.strawberry_topup_transform(
            observation(300),
            None,
            pre,
            post_unit_shed=shed(STRAWBERRY=3),
            future_actions=future,
            queued_commands=[],
        )
        self.assertEqual(post, pre)
        self.assertEqual(report["reason"], "requires_one_current_sell")

    def test_h4_uses_same_future_snapshot_as_h8(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True,
            strawberry_topup=True,
        )
        selected = action(market=[["SELL", "STRAWBERRY", 1]])
        stock = shed(STRAWBERRY=4)
        future = future_range(
            301, 308, market_by_step={301: [["SELL", "STRAWBERRY", 3]]}
        )
        pre, _ = component.sale_window_transform(
            observation(300),
            None,
            selected,
            post_unit_shed=stock,
            future_actions=future,
            queued_commands=[],
        )
        drifted = copy.deepcopy(future)
        drifted[301] = action(market=[["SELL", "STRAWBERRY", 99]])
        post, report = component.strawberry_topup_transform(
            observation(300),
            None,
            pre,
            post_unit_shed=stock,
            future_actions=drifted,
            queued_commands=[],
        )
        self.assertEqual(post, pre)
        self.assertEqual(report["reason"], "future_snapshot_mismatch")
        self.assertEqual(component.reservation_debts(0), {})

    def test_changed_h4_projection_recomputes_from_pre_h4_debt(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True,
            strawberry_topup=True,
        )
        selected = action(market=[["SELL", "STRAWBERRY", 1]])
        future = future_range(
            301, 308, market_by_step={301: [["SELL", "STRAWBERRY", 4]]}
        )
        pre, _ = component.sale_window_transform(
            observation(300),
            None,
            selected,
            post_unit_shed=shed(STRAWBERRY=5),
            future_actions=future,
            queued_commands=[],
        )
        first, _ = component.strawberry_topup_transform(
            observation(300),
            None,
            pre,
            post_unit_shed=shed(STRAWBERRY=5),
            future_actions=future,
            queued_commands=[],
        )
        self.assertEqual(first["market"], [["SELL", "STRAWBERRY", 5]])
        self.assertEqual(component.reservation_debts(0), {301: {"STRAWBERRY": 4}})

        changed, report = component.strawberry_topup_transform(
            observation(300),
            None,
            pre,
            post_unit_shed=shed(STRAWBERRY=3),
            future_actions=future,
            queued_commands=[],
        )
        self.assertEqual(changed["market"], [["SELL", "STRAWBERRY", 3]])
        self.assertEqual(report["reservations"], ((301, 2),))
        self.assertEqual(component.reservation_debts(0), {301: {"STRAWBERRY": 2}})


if __name__ == "__main__":
    unittest.main()
