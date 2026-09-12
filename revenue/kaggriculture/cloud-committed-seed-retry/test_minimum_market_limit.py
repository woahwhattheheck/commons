# SPDX-License-Identifier: Apache-2.0
"""Minimum-one executable-prefix parity for committed seed retry."""
from __future__ import annotations

from types import ModuleType, SimpleNamespace
import sys
import unittest

import seed_retry


class _Funding:
    @staticmethod
    def certify_seed_funding(mechanics, obs, candidate, without_retry, cfg):
        return {
            'status': 'certified',
            'reason': 'fixture',
            'original_fixed_cost_upper_bound': 100,
        }


MECHANICS = SimpleNamespace(CROPS={'STRAWBERRY': {'seed': 100}})
COMMITTED = {'farmer': ['PLANT', 'STRAWBERRY'], 'hands': [], 'market': []}
PASS = {'farmer': ['PASS'], 'hands': [], 'market': []}


def _obs():
    return {
        'step': 10,
        'player': 0,
        'farms': [{
            'money': 1000,
            'farmer': [0, 0],
            'hands': [],
            'hires_today': 0,
            'unlocked_quadrants': ['NW'],
            'tiles': [[None]],
        }],
        'private': {'seeds': {'STRAWBERRY': 0}},
        'market': {'inventory': {}, 'params': {}},
    }


class MinimumOneMarketLimitTests(unittest.TestCase):
    def test_zero_and_negative_limits_execute_one_row_but_keep_type_contract(self):
        for raw in (0, -1, -99):
            with self.subTest(raw=raw):
                self.assertEqual(seed_retry._market_limit({'maxMarketOrdersPerTurn': raw}), 1)
        self.assertEqual(seed_retry._market_limit({'maxMarketOrdersPerTurn': 3}), 3)
        for bad in (True, False, 1.0, '1', None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    seed_retry._market_limit({'maxMarketOrdersPerTurn': bad})

    def test_zero_and_negative_dynamic_product_veto_row_zero_only(self):
        for raw in (0, -7):
            maximum = seed_retry._market_limit({'maxMarketOrdersPerTurn': raw})
            with self.subTest(raw=raw, case='row0'):
                self.assertTrue(seed_retry._has_dynamic_product_obligation(
                    [[['BUY_PRODUCT', 'WHEAT', 1], []]], maximum))
            with self.subTest(raw=raw, case='row1_suffix'):
                self.assertFalse(seed_retry._has_dynamic_product_obligation(
                    [[[], ['BUY_PRODUCT', 'WHEAT', 1]]], maximum))

    def test_zero_and_negative_cash_reserve_counts_row_zero_not_row_one(self):
        scheduler = ModuleType('scheduler')

        def _order_spend(order, farm, inventory, params, hires, cfg):
            spend = order[2] if order and order[0] == 'BUY_SEED' else 0
            return spend, hires

        scheduler._order_spend = _order_spend
        scheduler.m = SimpleNamespace(LAND_ORDER=['NE', 'SW', 'SE'])
        previous = sys.modules.get('scheduler')
        sys.modules['scheduler'] = scheduler
        try:
            route = [PASS.copy() for _ in range(12)]
            route[11] = {'market': [['BUY_SEED', 'STRAWBERRY', 11],
                                    ['BUY_SEED', 'STRAWBERRY', 999]]}
            runtime = SimpleNamespace(
                controller=SimpleNamespace(R={'fixture': route}, cur='fixture'))
            selected = {'market': [['BUY_SEED', 'STRAWBERRY', 7],
                                   ['BUY_SEED', 'STRAWBERRY', 999]]}
            for raw in (0, -5):
                with self.subTest(raw=raw):
                    cfg = {'maxMarketOrdersPerTurn': raw}
                    self.assertEqual(
                        seed_retry._prefix_cash_reserve(runtime, _obs(), cfg, selected, 11),
                        18,
                    )
        finally:
            if previous is None:
                del sys.modules['scheduler']
            else:
                sys.modules['scheduler'] = previous

    def test_zero_and_negative_append_slot_is_row_zero_only(self):
        for raw in (0, -3):
            cfg = {
                'turnsPerDay': 24,
                'episodeSteps': 720,
                'maxMarketOrdersPerTurn': raw,
            }
            with self.subTest(raw=raw, case='empty_queue'):
                action, report = seed_retry.propose_seed_retry(
                    MECHANICS, _Funding(), _obs(), dict(PASS), COMMITTED, cfg,
                    reserved_cash=0, next_step=11)
                self.assertEqual(report['status'], 'appended')
                self.assertEqual(action['market'], [['BUY_SEED', 'STRAWBERRY', 1]])
            with self.subTest(raw=raw, case='row0_occupied'):
                selected = dict(PASS)
                selected['market'] = [[]]
                action, report = seed_retry.propose_seed_retry(
                    MECHANICS, _Funding(), _obs(), selected, COMMITTED, cfg,
                    reserved_cash=0, next_step=11)
                self.assertEqual(report['reason'], 'no_append_slot')
                self.assertEqual(action, selected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
