# SPDX-License-Identifier: Apache-2.0
"""Fast source gate for the default-OFF EOD capacity rescue theorem."""
from __future__ import annotations

import copy
import sys
import types
import unittest

from eod_capacity_rescue import apply_native_eod_capacity_rescue as rescue


STANDARD = {
    'boardSize': 10,
    'turnsPerDay': 24,
    'shedCapacity': 100,
    'maxMarketOrdersPerTurn': 10,
    'episodeSteps': 720,
    'townShopSellInterval': 4,
    'townCenterSellInterval': 24,
}


def fixture(*, step=23, shed=None, cargo=None, market=None):
    shed = dict(shed if shed is not None else {'MILK': 100})
    cargo = dict(cargo if cargo is not None else {'MILK': 5})
    farm = {
        'farmer': [0, 0],
        'hands': [],
        'tiles': [[None for _ in range(10)] for _ in range(10)],
        'money': 100,
    }
    obs = {
        'step': step,
        'player': 0,
        'farms': [farm, copy.deepcopy(farm)],
        'private': {
            'inventories': [dict(cargo)],
            'shed': dict(shed),
            'seeds': {},
        },
        'market': {'prices': {item: 4 for item in (
            'WHEAT', 'CARROT', 'TOMATO', 'STRAWBERRY', 'MELON',
            'EGG', 'MILK', 'WOOL', 'FERTILIZER')},
    }
    action = {'farmer': ['PASS'], 'hands': [], 'market': list(market or [])}
    return obs, action


class EODCapacityRescue(unittest.TestCase):
    def call(self, obs, action, *, projected=None, enabled=True, error=None):
        scheduler = types.ModuleType('scheduler')

        def post_units(_obs, _action, _configuration):
            if error is not None:
                raise error
            if projected is not None:
                return None, copy.deepcopy(projected)
            return None, {
                'shed': copy.deepcopy(obs['private']['shed']),
                'inventories': copy.deepcopy(obs['private']['inventories']),
            }

        scheduler.post_units = post_units
        prior = sys.modules.get('scheduler')
        sys.modules['scheduler'] = scheduler
        try:
            return rescue(action, obs, dict(STANDARD), enabled=enabled)
        finally:
            if prior is None:
                sys.modules.pop('scheduler', None)
            else:
                sys.modules['scheduler'] = prior

    def test_default_off_is_exact_identity(self):
        obs, action = fixture()
        result, info = rescue(action, obs, dict(STANDARD))
        self.assertIs(result, action)
        self.assertEqual(info, {'changed': False, 'reason': 'disabled'})

    def test_appends_only_minimum_overflow_without_mutation(self):
        obs, action = fixture(shed={'MILK': 98}, cargo={'MILK': 5})
        before_obs, before_action = copy.deepcopy(obs), copy.deepcopy(action)
        result, info = self.call(obs, action)
        self.assertEqual(info['rescued_units'], 3)
        self.assertEqual(result['market'], [['SELL', 'MILK', 3]])
        self.assertEqual(obs, before_obs)
        self.assertEqual(action, before_action)
        self.assertIsNot(result, action)

    def test_neutral_market_prefix_is_preserved(self):
        obs, action = fixture(market=[['HIRE'], ['BUY_SEED', 'WHEAT', 2]])
        result, info = self.call(obs, action)
        self.assertTrue(info['changed'])
        self.assertEqual(result['market'][:-1], action['market'])
        self.assertEqual(result['market'][-1], ['SELL', 'MILK', 5])

    def test_stock_changing_market_prefix_fails_closed(self):
        for market in ([['SELL', 'MILK', 1]], [['BUY_PRODUCT', 'MILK', 1]],
                       [['BUY_ANIMAL', 'COW', 1]], [['???']]):
            with self.subTest(market=market):
                obs, action = fixture(market=market)
                result, info = self.call(obs, action)
                self.assertIs(result, action)
                self.assertEqual(info['reason'], 'market_stock_or_unknown')

    def test_non_eod_and_terminal_tail_do_not_activate(self):
        for step in (0, 22, 24, 694, 696, 719):
            with self.subTest(step=step):
                obs, action = fixture(step=step)
                result, info = self.call(obs, action)
                self.assertIs(result, action)
                self.assertEqual(info['reason'], 'not_usable_eod')

    def test_requires_same_product_stock_to_back_sell(self):
        obs, action = fixture(shed={'WHEAT': 100}, cargo={'MILK': 5})
        result, info = self.call(obs, action)
        self.assertIs(result, action)
        self.assertEqual(info['reason'], 'insufficient_same_product')

    def test_projection_schema_errors_fail_closed(self):
        obs, action = fixture()
        result, info = self.call(obs, action, error=ValueError('bad projection'))
        self.assertIs(result, action)
        self.assertEqual(info['reason'], 'projection_schema')

    def test_deadline_like_exceptions_propagate(self):
        class DeadlineExceeded(Exception):
            pass

        obs, action = fixture()
        with self.assertRaises(DeadlineExceeded):
            self.call(obs, action, error=DeadlineExceeded('stop'))

    def test_market_capacity_is_reserved_before_append(self):
        obs, action = fixture(market=[[] for _ in range(10)])
        result, info = self.call(obs, action)
        self.assertIs(result, action)
        self.assertEqual(info['reason'], 'market_capacity')


if __name__ == '__main__':
    unittest.main()
