# SPDX-License-Identifier: Apache-2.0
"""Pinned-engine SELL grammar at the fertilizer operating-stock boundary."""
from copy import deepcopy
import unittest

import mechanics as m
from operating_stock import protect_operating_stock


class OperatingStockMarketGrammarTests(unittest.TestCase):
    def setUp(self):
        self.now = 460
        self.farm = {
            'farmer': [4, 4], 'hands': [[4, 4]], 'money': 50000,
            'tiles': [[None for _ in range(10)] for _ in range(10)],
        }
        for x in (2, 3):
            self.farm['tiles'][4][x] = {
                'kind': 'PLANT', 'crop': 'STRAWBERRY', 'planted_day': 10,
                'yield_units': 0, 'fertilized_until_day': -1,
                'max_lifespan_step': -1, 'consecutive_unwatered': 0,
                'watered_today': True,
            }
        self.private = {
            'inventories': [{}, {}], 'shed': {'FERTILIZER': 9}, 'seeds': {},
        }
        self.obs = {
            'step': self.now, 'player': 0, 'day': 19,
            'market': {'inventory': {'FERTILIZER': 10300, 'STRAWBERRY': 9900}},
        }
        self.selected = {
            'farmer': ['PASS'], 'hands': [['PASS']],
            'market': [['SELL', 'FERTILIZER', 9]],
        }
        self.route = [
            {'farmer': ['PASS'], 'hands': [['PASS']], 'market': []}
            for _ in range(720)
        ]
        self.route[461]['hands'][0] = ['PICKUP', 'FERTILIZER', 3]
        self.route[462]['hands'][0] = ['WEST']
        self.route[463]['hands'][0] = ['FERTILIZE']
        self.route[464]['hands'][0] = ['WEST']
        self.route[465]['hands'][0] = ['FERTILIZE']

    def propose(self):
        return protect_operating_stock(
            m, self.obs, {}, self.selected, self.farm,
            self.private, self.route, (226, 360, 433),
        )

    def test_engine_inert_uncoercible_fertilizer_sell_never_raises(self):
        self.selected['market'] = [
            ['SELL', 'FERTILIZER', 'not-a-number', 'opaque-receipt'],
        ]
        before = deepcopy(self.selected)
        result, report = self.propose()
        self.assertIs(result, self.selected)
        self.assertEqual(self.selected, before)
        self.assertFalse(report['changed'])
        self.assertEqual(report['reason'], 'no_fertilizer_sale')

    def test_valid_withholding_preserves_metadata_and_inert_sibling(self):
        inert = ['SELL', 'FERTILIZER', 'bad', {'receipt': 'keep-inert'}]
        metadata = {'receipt': ['keep', 1]}
        self.selected['market'] = [
            ['SELL', 'FERTILIZER', '9', 'ignored-by-engine', metadata],
            deepcopy(inert),
            ['SELL', 'WOOL', 1, 'unrelated-opaque'],
        ]
        before = deepcopy(self.selected)
        result, report = self.propose()
        self.assertTrue(report['changed'])
        self.assertEqual(
            result['market'][0],
            ['SELL', 'FERTILIZER', 7, 'ignored-by-engine', metadata],
        )
        self.assertEqual(result['market'][1], inert)
        self.assertEqual(result['market'][2], before['market'][2])
        self.assertEqual(self.selected, before)

    def test_float_quantity_uses_engine_int_coercion_and_keeps_tail(self):
        self.selected['market'] = [
            ['SELL', 'FERTILIZER', 9.9, 'opaque'],
        ]
        result, report = self.propose()
        self.assertTrue(report['changed'])
        self.assertEqual(result['market'], [['SELL', 'FERTILIZER', 7, 'opaque']])


if __name__ == '__main__':
    unittest.main()
