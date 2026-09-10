# SPDX-License-Identifier: Apache-2.0
"""Executable-prefix contracts for early-capital ordering."""
import copy
from pathlib import Path
import unittest

import mechanics as m
from early_capital import order_early_capital


CFG = {
    'episodeSteps': 720,
    'turnsPerDay': 24,
    'maxMarketOrdersPerTurn': 3,
}


def obs(step=1):
    return {
        'step': step,
        'day': step // 24,
        'hour': step % 24,
        'player': 0,
        'private': {'seeds': {}},
    }


def action(market):
    return {'farmer': ['PASS'], 'hands': [], 'market': copy.deepcopy(market)}


class EarlyCapitalExecutablePrefixContracts(unittest.TestCase):
    def test_suffix_capital_does_not_activate_transform(self):
        source = action([
            ['SELL', 'MILK', 1],
            ['HIRE'],
            ['BUY_PRODUCT', 'WHEAT', 1],
            ['BUY_LAND'],
        ])
        out, report = order_early_capital(None, obs(), CFG, source, None)
        self.assertIs(out, source)
        self.assertFalse(report['changed'])
        self.assertEqual(report['reason'], 'no_admitted_capital')
        self.assertEqual(report['active_rows'], 3)
        self.assertEqual(report['suffix_rows'], 1)

    def test_suffix_sell_cannot_enter_executable_prefix(self):
        source = action([
            ['BUY_PRODUCT', 'WHEAT', 1],
            ['BUY_LAND'],
            ['BUY_SEED', 'CARROT', 1],
            ['SELL', 'MILK', 7],
        ])
        out, report = order_early_capital(None, obs(), CFG, source, None)
        self.assertTrue(report['changed'])
        self.assertEqual(out['market'][:3], [
            ['BUY_LAND'],
            ['BUY_PRODUCT', 'WHEAT', 1],
            ['BUY_SEED', 'CARROT', 1],
        ])
        self.assertEqual(out['market'][3:], source['market'][3:])
        self.assertEqual(report['moved'], 2)

    def test_suffix_funding_cannot_evict_an_active_order(self):
        source = action([
            ['BUY_PRODUCT', 'WHEAT', 1],
            ['BUY_LAND'],
            ['PASS'],
            ['SELL', 'MILK', 7],
        ])
        out, _ = order_early_capital(None, obs(), CFG, source, None)
        self.assertEqual(
            sorted(map(tuple, out['market'][:3])),
            sorted(map(tuple, source['market'][:3])),
        )
        self.assertEqual(out['market'][3], ['SELL', 'MILK', 7])

    def test_zero_limit_matches_official_minimum_one(self):
        cfg = dict(CFG, maxMarketOrdersPerTurn=0)
        source = action([
            ['BUY_PRODUCT', 'WHEAT', 1],
            ['BUY_LAND'],
        ])
        out, report = order_early_capital(None, obs(), cfg, source, None)
        self.assertIs(out, source)
        self.assertEqual(report['active_limit'], 1)
        self.assertEqual(report['active_rows'], 1)
        self.assertEqual(report['reason'], 'no_admitted_capital')

    def test_fully_executable_list_retains_prior_ordering(self):
        cfg = dict(CFG, maxMarketOrdersPerTurn=10)
        source = action([
            ['BUY_PRODUCT', 'WHEAT', 1],
            ['BUY_LAND'],
            ['SELL', 'MILK', 7],
            ['HIRE'],
        ])
        out, report = order_early_capital(None, obs(), cfg, source, None)
        self.assertTrue(report['changed'])
        self.assertEqual(out['market'], [
            ['SELL', 'MILK', 7],
            ['HIRE'],
            ['BUY_LAND'],
            ['BUY_PRODUCT', 'WHEAT', 1],
        ])
        self.assertEqual(report['suffix_rows'], 0)

    def test_unknown_suffix_is_preserved_but_not_parsed(self):
        source = action([
            ['BUY_PRODUCT', 'WHEAT', 1],
            ['BUY_LAND'],
            ['PASS'],
            ['TELEPORT'],
        ])
        out, report = order_early_capital(None, obs(), CFG, source, None)
        self.assertTrue(report['changed'])
        self.assertEqual(out['market'][-1], ['TELEPORT'])

    def test_malformed_limit_fails_closed(self):
        source = action([['BUY_LAND'], ['SELL', 'MILK', 1]])
        for value in (True, 3.0, '3', None):
            with self.subTest(value=value):
                cfg = dict(CFG, maxMarketOrdersPerTurn=value)
                out, report = order_early_capital(None, obs(), cfg, source, None)
                self.assertIs(out, source)
                self.assertEqual(report['reason'], 'unsupported_market_limit')

    def test_returned_rows_do_not_alias_caller_input(self):
        source = action([
            ['BUY_PRODUCT', 'WHEAT', 1],
            ['BUY_LAND'],
            ['PASS'],
            ['SELL', 'MILK', 7],
        ])
        out, _ = order_early_capital(None, obs(), CFG, source, None)
        out['market'][0].append('mutated')
        out['market'][-1].append('mutated')
        self.assertEqual(source['market'][1], ['BUY_LAND'])
        self.assertEqual(source['market'][-1], ['SELL', 'MILK', 7])

    def test_inert_redundant_hire_sell_cannot_outrank_real_funding(self):
        redundant_source = Path('reference/titan-current/redundant_hire.py').read_text()
        self.assertIn('NO_ORDER = ["SELL", "WHEAT", 0]', redundant_source)

        source = action([
            ['BUY_LAND'],
            ['SELL', 'MELON', 0],
            ['SELL', 'MELON', 1],
        ])
        out, report = order_early_capital(None, obs(), CFG, source, None)
        self.assertTrue(report['changed'])
        self.assertEqual(out['market'], [
            ['SELL', 'MELON', 1],
            ['BUY_LAND'],
            ['SELL', 'MELON', 0],
        ])

        # Exact lockstep discontinuity: a rival row-0 MELON sale changes the
        # delayed row-1 quote by one dollar. At $750 starting cash that decides
        # whether the first $1,000 land purchase commits.
        simultaneous_quote = m.market_price('MELON', 10007, None)
        delayed_quote = m.market_price('MELON', 10008, None)
        self.assertEqual((simultaneous_quote, delayed_quote), (250, 249))
        self.assertEqual(750 + simultaneous_quote, 1000)
        self.assertEqual(750 + delayed_quote, 999)

    def test_nonpositive_and_malformed_sells_remain_inert(self):
        cfg = dict(CFG, maxMarketOrdersPerTurn=5)
        source = action([
            ['BUY_LAND'],
            ['SELL', 'MELON', 0],
            ['SELL', 'MELON', -1],
            ['SELL', 'MELON', 'not-a-number'],
            ['SELL', 'MELON', 1],
        ])
        out, _ = order_early_capital(None, obs(), cfg, source, None)
        self.assertEqual(out['market'], [
            ['SELL', 'MELON', 1],
            ['BUY_LAND'],
            ['SELL', 'MELON', 0],
            ['SELL', 'MELON', -1],
            ['SELL', 'MELON', 'not-a-number'],
        ])


if __name__ == '__main__':
    unittest.main()
