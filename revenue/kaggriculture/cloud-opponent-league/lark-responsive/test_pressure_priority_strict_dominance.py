"""Contracts for the conservative canonical market-pressure ordering mode."""
from __future__ import annotations

import copy
import unittest
from collections import Counter
import json

from pressure_priority import transform

BASE = {'MILK': 143, 'WOOL': 240, 'WHEAT': 50, 'FERTILIZER': 50}
SLOPE = {'MILK': 2, 'WOOL': 0, 'WHEAT': 1, 'FERTILIZER': 1}


def curve(item, stock, params=None):
    return max(1, BASE[item] - (params or {}).get('slope', SLOPE[item]) * stock)


def observation():
    return {'market': {'inventory': dict.fromkeys(BASE, 0), 'prices': BASE.copy()}}


def apply(action, *, strict=True, obs=None, cfg=None, rival_supply=None):
    return transform(
        action,
        observation() if obs is None else obs,
        {} if cfg is None else cfg,
        quote=curve,
        rival_supply=rival_supply,
        strict_dominance=strict,
    )


class StrictDominancePressureTests(unittest.TestCase):
    def test_historical_default_retains_full_pressure_sort(self):
        action = {'market': [['SELL', 'WHEAT', 2], ['SELL', 'FERTILIZER', 3]]}
        self.assertEqual(apply(action, strict=False)['market'], action['market'][::-1])

    def test_two_exposed_lots_keep_parent_relative_order(self):
        action = {'market': [['SELL', 'WHEAT', 2], ['SELL', 'FERTILIZER', 3]]}
        # Both scores are positive (4 and 9). Their proxy magnitudes do not
        # prove which commodity is safe to demote against unseen rival slots.
        self.assertEqual(apply(action)['market'], action['market'])

    def test_exposed_lot_crosses_only_zero_exposure_lot(self):
        action = {'market': [
            ['SELL', 'WOOL', 14],       # flat curve: zero exposure
            ['SELL', 'MILK', 15],       # decreasing curve: positive exposure
            ['SELL', 'WHEAT', 2],       # positive exposure
        ]}
        self.assertEqual(apply(action)['market'], [
            ['SELL', 'MILK', 15],
            ['SELL', 'WHEAT', 2],
            ['SELL', 'WOOL', 14],
        ])

    def test_barriers_prefix_and_positive_order_are_preserved(self):
        action = {'farmer': ['PASS'], 'hands': [['CARE']], 'market': [
            ['SELL', 'WHEAT', 2], ['SELL', 'FERTILIZER', 3],
            ['HIRE'],
            ['SELL', 'WOOL', 14], ['SELL', 'MILK', 15],
            ['SELL', 'MILK', 1],
        ]}
        before = copy.deepcopy(action)
        out = apply(action, cfg={'maxMarketOrdersPerTurn': 5})
        self.assertEqual(out['market'], [
            ['SELL', 'WHEAT', 2], ['SELL', 'FERTILIZER', 3],
            ['HIRE'],
            ['SELL', 'MILK', 15], ['SELL', 'WOOL', 14],
            ['SELL', 'MILK', 1],
        ])
        self.assertEqual(action, before)
        self.assertEqual(out['farmer'], action['farmer'])
        self.assertEqual(out['hands'], action['hands'])
        self.assertEqual(
            Counter(map(json.dumps, out['market'])),
            Counter(map(json.dumps, action['market'])),
        )

    def test_explicit_public_zero_flow_keeps_parent_order(self):
        action = {'market': [['SELL', 'WOOL', 2], ['SELL', 'MILK', 2]]}
        self.assertEqual(
            apply(action, rival_supply={'WOOL': 0, 'MILK': 0}),
            action,
        )

    def test_mode_flag_must_be_boolean(self):
        action = {'market': [['SELL', 'MILK', 2]]}
        for value in (1, 0, None, 'yes', [], {}):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'strict_dominance'):
                    apply(action, strict=value)


if __name__ == '__main__':
    unittest.main(verbosity=2)
