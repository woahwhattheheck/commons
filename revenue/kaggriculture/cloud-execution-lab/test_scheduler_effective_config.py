# SPDX-License-Identifier: Apache-2.0
"""Production convergence tests for scheduler engine/config custody."""
from __future__ import annotations

import inspect
import types
import unittest
from unittest import mock

import scheduler


class SchedulerEffectiveConfigTests(unittest.TestCase):
    def test_strict_projection_calendar_preserves_default_and_rejects_poison(self):
        self.assertEqual(scheduler._strict_scheduler_turns_per_day({}), 24)
        self.assertEqual(scheduler._strict_scheduler_turns_per_day({'turnsPerDay': 24}), 24)
        self.assertEqual(scheduler._strict_scheduler_turns_per_day({'turnsPerDay': 12}), 12)
        for bad in (True, False, 0, -1, 24.0, '24', None, [24], {'value': 24}):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    scheduler._strict_scheduler_turns_per_day({'turnsPerDay': bad})
        with self.assertRaises(ValueError):
            scheduler._strict_scheduler_turns_per_day(None)

    def test_market_prefix_matches_engine_minimum_one_raw_slot_limit(self):
        action = {'market': [[], ['SELL', 'MILK', 2], ['HIRE']]}
        for cap in (0, -7, 1):
            with self.subTest(cap=cap):
                self.assertEqual(scheduler._engine_market_limit({'maxMarketOrdersPerTurn': cap}), 1)
                self.assertEqual(
                    scheduler._engine_market_prefix(action, {'maxMarketOrdersPerTurn': cap}),
                    [[]],
                )
        self.assertEqual(
            scheduler._engine_market_prefix(action, {'maxMarketOrdersPerTurn': 2}),
            [[], ['SELL', 'MILK', 2]],
        )
        self.assertEqual(scheduler._engine_market_prefix({'market': 'bad'}, {}), [])
        self.assertEqual(scheduler._engine_market_prefix(None, {}), [])

    def test_absorption_clamps_shop_and_center_intervals_like_engine(self):
        # PET_CAFE is a one-product shop, so CARROT consumption multiplier is 2.
        for raw in (0, -9, 1, '1', 1.9):
            with self.subTest(shop_interval=raw):
                got = scheduler.absorption(
                    'CARROT', 1, ['PET_CAFE'],
                    {'townShopSellInterval': raw, 'townCenterSellInterval': 999},
                )
                self.assertEqual(got, 2)
        for raw in (0, -3, 1, '1', 1.2):
            with self.subTest(center_interval=raw):
                got = scheduler.absorption(
                    'CARROT', 1, [],
                    {'townShopSellInterval': 999, 'townCenterSellInterval': raw},
                )
                self.assertEqual(got, 1)
        self.assertEqual(
            scheduler.absorption(
                'FERTILIZER', 1, [],
                {'townShopSellInterval': 999, 'townCenterSellInterval': 0},
            ),
            0,
        )

    def test_cash_reserve_uses_engine_prefix_not_full_queue(self):
        obj = scheduler.SellScheduler.__new__(scheduler.SellScheduler)
        obj.controller = types.SimpleNamespace(R=[[]], cur=0)
        obs = {
            'step': 0,
            'player': 0,
            'farms': [{'unlocked_quadrants': ['NW'], 'hires_today': 0}],
            'market': {'inventory': {}, 'params': {}},
        }
        base = {'market': [[], ['HIRE'], ['BUY_LAND']]}
        calls = []

        def spend(order, farm, inventory, params, hires, config):
            calls.append(order)
            return 0, hires

        with mock.patch.object(scheduler, '_order_spend', side_effect=spend):
            self.assertEqual(
                obj.cash_reserve(obs, {'maxMarketOrdersPerTurn': 1, 'turnsPerDay': 24}, base, 0),
                0,
            )
        self.assertEqual(calls, [[]])

    def test_cash_reserve_hire_reset_uses_configured_day_boundary(self):
        obj = scheduler.SellScheduler.__new__(scheduler.SellScheduler)
        route = [{'market': []} for _ in range(13)]
        route[11] = {'market': [['HIRE']]}
        route[12] = {'market': [['HIRE']]}
        obj.controller = types.SimpleNamespace(R=[route], cur=0)
        obs = {
            'step': 10,
            'player': 0,
            'farms': [{'unlocked_quadrants': ['NW'], 'hires_today': 3}],
            'market': {'inventory': {}, 'params': {}},
        }
        seen_hires = []

        def spend(order, farm, inventory, params, hires, config):
            if order and order[0] == 'HIRE':
                seen_hires.append(hires)
                return 0, hires + 1
            return 0, hires

        with mock.patch.object(scheduler, '_order_spend', side_effect=spend):
            obj.cash_reserve(obs, {'turnsPerDay': 12}, {'market': []}, 12)
        self.assertEqual(seen_hires, [3, 0])

    def test_production_source_has_complete_calendar_and_sale_prefix_convergence(self):
        post = inspect.getsource(scheduler.post_units)
        cash = inspect.getsource(scheduler.SellScheduler.cash_reserve)
        profile = inspect.getsource(scheduler.SellScheduler.receipt_profile)
        act = inspect.getsource(scheduler.SellScheduler.act)

        self.assertIn('turns_per_day=_strict_scheduler_turns_per_day(config)', post)
        self.assertNotIn("int(config.get('turnsPerDay',24))", post)

        self.assertIn('orders=_engine_market_prefix(market_action,config)', cash)
        self.assertIn('t%turns_per_day==0', cash)
        self.assertNotIn('t%24==0', cash)

        self.assertIn('orders=_engine_market_prefix(market_action,config)', profile)
        self.assertIn('t//turns_per_day,turns_per_day', profile)
        self.assertIn('t%turns_per_day==turns_per_day-1', profile)
        self.assertNotIn('t//24,24', profile)
        self.assertNotIn('t%24==23', profile)

        for required in (
            'market_limit=_engine_market_limit(config)',
            '(now//turns_per_day+1)*turns_per_day-1',
            'for o in _engine_market_prefix(base,config)',
            'for order in _engine_market_prefix(future_action,config)',
            'orders=_engine_market_prefix(market_action,config)',
            'if slot>=market_limit',
            'if q>0 and len(market)<market_limit',
            'sold=sum(o[2] for o in _engine_market_prefix(out,config)',
        ):
            self.assertIn(required, act)
        self.assertNotIn('now//24+1', act)
        self.assertNotIn('now%24==23', act)
        self.assertNotIn("len(orders)>=int(config.get('maxMarketOrdersPerTurn',10))", act)
        self.assertNotIn("len(market)<int(config.get('maxMarketOrdersPerTurn',10))", act)

    def test_replay_safe_wrapper_contract_survives_convergence(self):
        source = inspect.getsource(scheduler.agent) + inspect.getsource(scheduler.naive_agent)
        self.assertIn('now<_LAST_STEP', source)
        self.assertIn('now<_NAIVE_LAST_STEP', source)
        self.assertNotIn('now==0', source)
        self.assertNotIn("int(obs.get('step',0))==0", source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
