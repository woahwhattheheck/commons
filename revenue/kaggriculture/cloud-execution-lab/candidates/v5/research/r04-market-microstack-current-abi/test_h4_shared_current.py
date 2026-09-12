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
from test_support import action, authority, future_range, observation, shed


class H4SharedLedgerTests(unittest.TestCase):
    def _stage(self, component, *, stock=None, future=None):
        obs = observation(300)
        selected = action(market=[["SELL", "STRAWBERRY", 1]])
        stock = shed(STRAWBERRY=4) if stock is None else stock
        future = (
            future_range(
                301,
                308,
                market_by_step={301: [["SELL", "STRAWBERRY", 3]]},
            )
            if future is None
            else future
        )
        route = authority(obs, future)
        pre, sale_report = component.sale_window_transform(
            obs,
            None,
            selected,
            post_unit_shed=stock,
            route_authority=route,
        )
        post, h4_report = component.strawberry_topup_transform(
            obs,
            None,
            pre,
            post_unit_shed=stock,
            route_authority=route,
        )
        return obs, route, pre, sale_report, post, h4_report

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
            sale_window=True, strawberry_topup=True
        )
        obs = observation(300)
        future = future_range(
            301, 308, market_by_step={301: [["SELL", "STRAWBERRY", 3]]}
        )
        route = authority(obs, future)
        selected = action(market=[["SELL", "STRAWBERRY", 1]])
        result, report = component.strawberry_topup_transform(
            obs,
            None,
            selected,
            post_unit_shed=shed(STRAWBERRY=4),
            route_authority=route,
        )
        self.assertEqual(result, selected)
        self.assertEqual(report["reason"], "requires_same_step_sale_window_stage")

    def test_existing_strawberry_row_tops_up_from_authenticated_future_sale(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True, strawberry_topup=True
        )
        _obs, _route, pre, sale_report, post, report = self._stage(component)
        self.assertEqual(pre["market"], [["SELL", "STRAWBERRY", 1]])
        self.assertEqual(post["market"], [["SELL", "STRAWBERRY", 4]])
        self.assertTrue(report["changed"])
        self.assertEqual(report["reservations"], ((301, 3),))
        self.assertEqual(
            component.reservation_debts(0), {301: {"STRAWBERRY": 3}}
        )
        self.assertEqual(
            report["route_authority_sha256"],
            sale_report["route_authority_sha256"],
        )

    def test_h4_exact_retry_is_idempotent_and_does_not_double_reserve(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True, strawberry_topup=True
        )
        obs, route, pre, _sale_report, first, first_report = self._stage(component)
        second, second_report = component.strawberry_topup_transform(
            copy.deepcopy(obs),
            None,
            copy.deepcopy(pre),
            post_unit_shed=shed(STRAWBERRY=4),
            route_authority=route,
        )
        self.assertEqual(second, first)
        self.assertEqual(second_report, first_report)
        self.assertEqual(
            component.reservation_debts(0), {301: {"STRAWBERRY": 3}}
        )

    def test_due_debt_is_repaid_by_h8_before_fresh_h4(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True, strawberry_topup=True
        )
        self._stage(component)
        obs301 = observation(301)
        route301 = authority(obs301)
        due, sale_report = component.sale_window_transform(
            obs301,
            None,
            action(market=[["SELL", "STRAWBERRY", 3]]),
            post_unit_shed=shed(STRAWBERRY=3),
            route_authority=route301,
        )
        self.assertEqual(due["market"], [])
        self.assertEqual(component.reservation_debts(0), {})
        self.assertTrue(sale_report["sales_first_changed"])

        h4, h4_report = component.strawberry_topup_transform(
            obs301,
            None,
            due,
            post_unit_shed=shed(STRAWBERRY=3),
            route_authority=route301,
        )
        self.assertEqual(h4, due)
        self.assertEqual(h4_report["reason"], "requires_one_current_sell")
        self.assertEqual(component.reservation_debts(0), {})

    def test_h4_cannot_create_a_new_strawberry_row(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True, strawberry_topup=True
        )
        obs = observation(300)
        future = future_range(
            301, 308, market_by_step={301: [["SELL", "STRAWBERRY", 3]]}
        )
        route = authority(obs, future)
        blocked_action = action(farmer=["PICKUP", "STRAWBERRY"])
        pre, _ = component.sale_window_transform(
            obs,
            None,
            blocked_action,
            post_unit_shed=shed(STRAWBERRY=3),
            route_authority=route,
        )
        post, report = component.strawberry_topup_transform(
            obs,
            None,
            pre,
            post_unit_shed=shed(STRAWBERRY=3),
            route_authority=route,
        )
        self.assertEqual(post, pre)
        self.assertEqual(report["reason"], "requires_one_current_sell")

    def test_h4_rejects_different_route_authority_than_h8(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True, strawberry_topup=True
        )
        obs = observation(300)
        first_future = future_range(
            301, 308, market_by_step={301: [["SELL", "STRAWBERRY", 3]]}
        )
        first_route = authority(obs, first_future)
        pre, _ = component.sale_window_transform(
            obs,
            None,
            action(market=[["SELL", "STRAWBERRY", 1]]),
            post_unit_shed=shed(STRAWBERRY=4),
            route_authority=first_route,
        )
        drifted_future = future_range(
            301, 308, market_by_step={301: [["SELL", "STRAWBERRY", 4]]}
        )
        drifted_route = authority(obs, drifted_future)
        post, report = component.strawberry_topup_transform(
            obs,
            None,
            pre,
            post_unit_shed=shed(STRAWBERRY=4),
            route_authority=drifted_route,
        )
        self.assertEqual(post, pre)
        self.assertEqual(report["reason"], "route_authority_mismatch")
        self.assertEqual(component.reservation_debts(0), {})

    def test_changed_h4_projection_recomputes_from_pre_h4_debt(self):
        component = R04MarketMicrostackCurrentABI(
            sale_window=True, strawberry_topup=True
        )
        obs = observation(300)
        future = future_range(
            301, 308, market_by_step={301: [["SELL", "STRAWBERRY", 4]]}
        )
        route = authority(obs, future)
        pre, _ = component.sale_window_transform(
            obs,
            None,
            action(market=[["SELL", "STRAWBERRY", 1]]),
            post_unit_shed=shed(STRAWBERRY=5),
            route_authority=route,
        )
        first, _ = component.strawberry_topup_transform(
            obs,
            None,
            pre,
            post_unit_shed=shed(STRAWBERRY=5),
            route_authority=route,
        )
        self.assertEqual(first["market"], [["SELL", "STRAWBERRY", 5]])
        self.assertEqual(
            component.reservation_debts(0), {301: {"STRAWBERRY": 4}}
        )

        changed, report = component.strawberry_topup_transform(
            obs,
            None,
            pre,
            post_unit_shed=shed(STRAWBERRY=3),
            route_authority=route,
        )
        self.assertEqual(changed["market"], [["SELL", "STRAWBERRY", 3]])
        self.assertEqual(report["reservations"], ((301, 2),))
        self.assertEqual(
            component.reservation_debts(0), {301: {"STRAWBERRY": 2}}
        )


if __name__ == "__main__":
    unittest.main()
