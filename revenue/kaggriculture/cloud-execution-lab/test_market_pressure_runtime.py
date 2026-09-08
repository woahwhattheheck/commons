# SPDX-License-Identifier: Apache-2.0
"""Runtime boundary checks for the landed LARK final SELL ordering."""
from __future__ import annotations

import unittest

from titan_runtime import Features, TitanAgent


class MarketPressureRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.obs = {
            'player': 0,
            'step': 100,
            'market': {
                # Exact default-curve quotes at the official initial stock.
                'inventory': {'WOOL': 10000, 'MILK': 10000},
                'prices': {'WOOL': 200, 'MILK': 160},
            },
        }
        self.cfg = {'maxMarketOrdersPerTurn': 10}

    def test_disabled_is_identity_without_copy(self):
        action = {'farmer': ['PASS'], 'hands': [],
                  'market': [['SELL', 'WOOL', 14], ['SELL', 'MILK', 15]]}
        agent = TitanAgent(Features(market_pressure=False))
        self.assertIs(agent._market_pressure_selected(self.obs, self.cfg, action), action)

    def test_enabled_uses_public_curve_and_preserves_barriers(self):
        action = {
            'farmer': ['PASS'],
            'hands': [['CARE']],
            'market': [
                ['SELL', 'WOOL', 14], ['SELL', 'MILK', 15],
                ['HIRE'], ['SELL', 'WOOL', 2], ['SELL', 'MILK', 2],
            ],
        }
        agent = TitanAgent(Features(market_pressure=True))
        result = agent._market_pressure_selected(self.obs, self.cfg, action)
        self.assertEqual(result['market'], [
            ['SELL', 'MILK', 15], ['SELL', 'WOOL', 14],
            ['HIRE'], ['SELL', 'MILK', 2], ['SELL', 'WOOL', 2],
        ])
        self.assertEqual(result['farmer'], action['farmer'])
        self.assertEqual(result['hands'], action['hands'])
        self.assertEqual(agent.diagnostics['market_pressure'],
                         {'enabled': True, 'changed': True})
        self.assertEqual(action['market'][0], ['SELL', 'WOOL', 14])


if __name__ == '__main__':
    unittest.main(verbosity=2)
