# SPDX-License-Identifier: Apache-2.0
"""E13 funded-prefix working-capital regressions."""
import copy
import unittest

import frozen_selected as fs


class FundedPrefixTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            'shedCapacity': 100,
            'farmHandCostMult': 1,
            'maxMarketOrdersPerTurn': 10,
            'turnsPerDay': 24,
            'episodeSteps': 720,
        }
        self.now = 5
        self.inventory = {item: 10000 for item in fs.m.PRODUCTS}
        self.farm = {
            'money': 0,
            'unlocked_quadrants': ['SOUTHEAST'],
            'hires_today': 0,
            'tiles': [[None for _ in range(10)] for _ in range(10)],
            'hands': [],
        }
        shed = {item: 0 for item in fs.m.PRODUCTS + list(fs.m.ANIMALS)}
        self.private = {
            'shed': shed,
            'seeds': {item: 0 for item in fs.m.CROPS},
            'inventories': [],
        }
        self.obs = {
            'step': self.now,
            'player': 0,
            'market': {'inventory': self.inventory, 'params': None},
        }
        self.route = [{} for _ in range(32)]

    def minimum(self, market, current, item='MILK', end=None):
        base = {'market': copy.deepcopy(market)}
        targets = {name: max(0, int(q)) for name, q in self.private['shed'].items()
                   if name in fs.PRODUCTS and q > 0}
        return fs.funded_minimum_now(
            self.obs, self.config, base, self.farm, self.private,
            self.route, self.now if end is None else end,
            current, targets, item,
        )

    def test_sale_before_buy_funds_only_needed_units(self):
        self.private['shed']['MILK'] = 10
        minimum, certificate = self.minimum(
            [['SELL', 'MILK', 10], ['BUY_ANIMAL', 'COW', 1]], {'MILK': 10})
        self.assertEqual(minimum, 3)
        self.assertEqual(certificate['reference_acquisitions'], 1)
        self.assertFalse(certificate['fallback'])

    def test_later_sale_never_prefunds_earlier_buy(self):
        self.private['shed']['MILK'] = 10
        minimum, certificate = self.minimum(
            [['BUY_ANIMAL', 'COW', 1], ['SELL', 'MILK', 10]], {'MILK': 10})
        self.assertEqual(minimum, 0)
        self.assertEqual(certificate['reference_acquisitions'], 0)

    def test_clipped_purchase_does_not_reserve_impossible_tail(self):
        self.farm['money'] = 1000
        self.private['shed']['MILK'] = 10
        self.private['shed']['WHEAT'] = 89
        minimum, certificate = self.minimum(
            [['BUY_ANIMAL', 'COW', 5], ['SELL', 'MILK', 10]], {'MILK': 10})
        self.assertEqual(minimum, 0)
        self.assertEqual(certificate['reference_acquisitions'], 1)

    def test_input_price_stress_is_part_of_certificate(self):
        self.private['shed']['MILK'] = 3
        minimum, certificate = self.minimum(
            [['SELL', 'MILK', 3], ['BUY_PRODUCT', 'FERTILIZER', 3]], {'MILK': 3})
        self.assertEqual(minimum, 3)
        self.assertEqual(certificate['stress_units'], 32)
        self.assertFalse(certificate['fallback'])

    def test_future_sale_bounds_commitment_prefix(self):
        self.private['shed']['MILK'] = 10
        self.private['shed']['WOOL'] = 1
        self.route[self.now + 1] = {'market': [['SELL', 'WOOL', 1]]}
        self.route[self.now + 2] = {'market': [['BUY_ANIMAL', 'COW', 1]]}
        minimum, certificate = self.minimum(
            [['SELL', 'MILK', 10]], {'MILK': 10}, end=self.now + 2)
        self.assertEqual(minimum, 0)
        self.assertEqual(certificate['funding_turn'], self.now + 1)
        self.assertEqual(certificate['prefix_end'], self.now)

    def test_purchase_before_next_funding_event_is_preserved(self):
        self.private['shed']['MILK'] = 10
        self.private['shed']['WOOL'] = 1
        self.route[self.now + 1] = {'market': [['BUY_ANIMAL', 'COW', 1]]}
        self.route[self.now + 2] = {'market': [['SELL', 'WOOL', 1]]}
        minimum, certificate = self.minimum(
            [['SELL', 'MILK', 10]], {'MILK': 10}, end=self.now + 2)
        self.assertEqual(minimum, 3)
        self.assertEqual(certificate['funding_turn'], self.now + 2)


if __name__ == '__main__':
    unittest.main()
