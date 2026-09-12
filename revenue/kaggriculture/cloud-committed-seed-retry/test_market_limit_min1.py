# SPDX-License-Identifier: Apache-2.0
"""Predecessor killers for official min-one market-prefix semantics."""
from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

import seed_retry


class _Mechanics:
    CROPS = {'STRAWBERRY': {'seed': 100}}


class _Funding:
    @staticmethod
    def certify_seed_funding(mechanics, obs, candidate, without_retry, cfg):
        return {
            'status': 'certified',
            'reason': 'ok',
            'original_fixed_cost_upper_bound': 100,
        }


def _obs():
    return {
        'step': 10,
        'player': 0,
        'farms': [{
            'money': 1000,
            'farmer': [0, 0],
            'hands': [],
            'tiles': [[None]],
            'unlocked_quadrants': [],
            'hires_today': 0,
        }],
        'private': {'seeds': {'STRAWBERRY': 0}},
        'market': {'inventory': {}, 'params': {}},
    }


class MarketLimitMinOneTests(unittest.TestCase):
    def test_zero_and_negative_limits_normalize_to_one_but_types_stay_strict(self):
        for raw in (0, -1, -999):
            with self.subTest(raw=raw):
                self.assertEqual(
                    seed_retry._market_limit({'maxMarketOrdersPerTurn': raw}), 1)
        for raw in (True, False, 1.0, '1', None):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    seed_retry._market_limit({'maxMarketOrdersPerTurn': raw})
        self.assertEqual(seed_retry._market_limit({}), 10)

    def test_dynamic_buy_product_veto_reads_row_zero_only(self):
        for raw in (0, -7):
            maximum = seed_retry._market_limit({'maxMarketOrdersPerTurn': raw})
            with self.subTest(raw=raw, position='row0'):
                self.assertTrue(seed_retry._has_dynamic_product_obligation([
                    [['BUY_PRODUCT', 'WHEAT', 1], ['SELL', 'WHEAT', 1]],
                ], maximum))
            with self.subTest(raw=raw, position='row1'):
                self.assertFalse(seed_retry._has_dynamic_product_obligation([
                    [['SELL', 'WHEAT', 1], ['BUY_PRODUCT', 'WHEAT', 999]],
                ], maximum))

    def test_cash_reserve_reads_row_zero_and_ignores_suffix(self):
        scheduler = ModuleType('scheduler')

        def order_spend(order, farm, inventory, params, hires, cfg):
            if order and order[0] == 'BUY_SEED':
                return 10 * int(order[2]), hires
            if order and order[0] == 'BUY_PRODUCT':
                return 9999, hires
            return 0, hires

        scheduler._order_spend = order_spend
        scheduler.m = SimpleNamespace(LAND_ORDER=[])
        route = [{} for _ in range(12)]
        route[11] = {'market': [
            ['BUY_SEED', 'STRAWBERRY', 2],
            ['BUY_PRODUCT', 'WHEAT', 999],
        ]}
        runtime = SimpleNamespace(
            controller=SimpleNamespace(R={'fixture': route}, cur='fixture'))
        obs = _obs()
        for raw in (0, -4):
            cfg = {'maxMarketOrdersPerTurn': raw}
            with self.subTest(raw=raw), patch.dict(sys.modules, {'scheduler': scheduler}):
                self.assertEqual(
                    seed_retry._prefix_cash_reserve(
                        runtime, obs, cfg, {'market': []}, 11),
                    20,
                )

    def test_append_slot_is_row_zero_or_nothing(self):
        committed = {
            'farmer': ['PLANT', 'STRAWBERRY'],
            'hands': [],
            'market': [],
        }
        for raw in (0, -5):
            cfg = {
                'maxMarketOrdersPerTurn': raw,
                'turnsPerDay': 24,
                'episodeSteps': 720,
            }
            with self.subTest(raw=raw, state='empty_prefix'):
                action, report = seed_retry.propose_seed_retry(
                    _Mechanics, _Funding, _obs(),
                    {'farmer': ['PASS'], 'hands': [], 'market': []},
                    committed, cfg, reserved_cash=0, next_step=11)
                self.assertEqual(report['status'], 'appended')
                self.assertEqual(
                    action['market'], [['BUY_SEED', 'STRAWBERRY', 1]])
            with self.subTest(raw=raw, state='row0_occupied_row1_inert'):
                selected = {
                    'farmer': ['PASS'],
                    'hands': [],
                    'market': [[], ['BUY_PRODUCT', 'WHEAT', 999]],
                }
                action, report = seed_retry.propose_seed_retry(
                    _Mechanics, _Funding, _obs(), selected,
                    committed, cfg, reserved_cash=0, next_step=11)
                self.assertEqual(action, selected)
                self.assertEqual(report['reason'], 'no_append_slot')


if __name__ == '__main__':
    unittest.main(verbosity=2)
