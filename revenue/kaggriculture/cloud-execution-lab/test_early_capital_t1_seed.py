# SPDX-License-Identifier: Apache-2.0
"""T-1 seed-causality regressions for canonical early-capital ordering."""
from copy import deepcopy
import unittest

import mechanics as m
from early_capital import _plant_demand, order_early_capital


def farm(money=3000, unlocked=('NW',), hires=0):
    return {
        'money': money,
        'unlocked_quadrants': list(unlocked),
        'hires_today': hires,
        'tiles': [[None] * 10 for _ in range(10)],
        'farmer': (4, 4),
        'hands': [],
    }


def obs(step=1, money=2643, unlocked=('NW',), seeds=None, player=0,
        shed=None, inventories=None):
    own = farm(money, unlocked)
    rival = farm(3000)
    stock = ({product: 10 for product in m.PRODUCTS} if shed is None
             else {product: 0 for product in m.PRODUCTS})
    if shed is not None:
        stock.update(shed)
    return {
        'step': step,
        'day': step // 24,
        'hour': step % 24,
        'player': player,
        'farms': [own, rival] if player == 0 else [rival, own],
        'private': {
            'shed': stock,
            'inventories': deepcopy(inventories) if inventories is not None else [{}],
            'seeds': dict(seeds or {}),
        },
        'market': {
            'inventory': {product: 10000 for product in m.PRODUCTS},
            'prices': {},
            'params': None,
        },
    }


CFG = {
    'episodeSteps': 720,
    'turnsPerDay': 24,
    'farmHandCostMult': 1,
    'maxMarketOrdersPerTurn': 10,
    'shedCapacity': 100,
    'boardSize': 10,
}


def empty_route():
    return [
        {'farmer': ['PASS'], 'hands': [], 'market': []}
        for _ in range(720)
    ]


class EarlyCapitalT1SeedCausality(unittest.TestCase):
    def test_demand_excludes_selected_unit_stage_but_counts_future_route(self):
        selected = {'farmer': ['PLANT', 'MELON'], 'hands': [], 'market': []}
        route = empty_route()
        route[151]['farmer'] = ['PLANT', 'CARROT']
        self.assertEqual(
            _plant_demand(selected, route, now=150, end=174),
            {'CARROT': 1},
        )

    def test_current_tick_plant_does_not_reserve_too_late_seed_order(self):
        selected = {
            'farmer': ['PLANT', 'MELON'],
            'hands': [],
            'market': [['BUY_SEED', 'MELON', 1], ['BUY_LAND']],
        }
        result, report = order_early_capital(
            m,
            obs(150, money=1500, unlocked=['NW'], seeds={}),
            CFG,
            selected,
            empty_route(),
        )
        self.assertTrue(report['changed'])
        self.assertEqual(report['reason'], 'ordered')
        self.assertEqual(result['market'][0], ['BUY_LAND'])
        self.assertEqual(result['market'][1], ['BUY_SEED', 'MELON', 1])
        self.assertEqual(result['farmer'], selected['farmer'])
        self.assertEqual(report['capital_funding']['reason'], 'certified')

    def test_next_tick_plant_still_reserves_seed_before_capital(self):
        selected = {
            'farmer': ['PASS'],
            'hands': [],
            'market': [['BUY_SEED', 'MELON', 1], ['BUY_LAND']],
        }
        route = empty_route()
        route[151]['farmer'] = ['PLANT', 'MELON']
        result, report = order_early_capital(
            m,
            obs(150, money=1500, unlocked=['NW'], seeds={}),
            CFG,
            selected,
            route,
        )
        self.assertFalse(report['changed'])
        self.assertEqual(report['reason'], 'already_ordered')
        self.assertEqual(result['market'][0], ['BUY_SEED', 'MELON', 1])
        self.assertEqual(result['market'][1], ['BUY_LAND'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
