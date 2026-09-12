# SPDX-License-Identifier: Apache-2.0
"""Regression for engine-order seed consumption in early-capital projection."""
import unittest
from copy import deepcopy

import mechanics as m
from early_capital import _project_post_unit_private, order_early_capital


CFG = {
    'episodeSteps': 720,
    'turnsPerDay': 24,
    'farmHandCostMult': 1,
    'maxMarketOrdersPerTurn': 10,
    'shedCapacity': 100,
    'boardSize': 10,
}


def observation():
    tiles = [[None] * 10 for _ in range(10)]
    farm = {
        'money': 5000,
        'unlocked_quadrants': ['NW'],
        'hires_today': 1,
        'tiles': tiles,
        'farmer': [4, 4],
        'hands': [[5, 4]],
    }
    rival = deepcopy(farm)
    return {
        'step': 1,
        'day': 0,
        'hour': 1,
        'player': 0,
        'farms': [farm, rival],
        'private': {
            'shed': {},
            'inventories': [{}, {}],
            'seeds': {'CARROT': 1},
        },
        'market': {'inventory': {p: 10000 for p in m.PRODUCTS},
                   'prices': {}, 'params': None},
    }


def selected_action():
    return {
        'farmer': ['PLANT', 'CARROT'],
        'hands': [['PLANT', 'CARROT']],
        'market': [['BUY_LAND'], ['BUY_SEED', 'CARROT', 1]],
    }


def route():
    rows = [{'farmer': ['PASS'], 'hands': [], 'market': []}
            for _ in range(720)]
    rows[2] = {'farmer': ['PLANT', 'CARROT'], 'hands': [], 'market': []}
    return rows


class EarlyCapitalSequentialSeedParity(unittest.TestCase):
    def test_unit_projection_consumes_available_seed_in_actor_order(self):
        public = observation()
        selected = selected_action()
        before_public = deepcopy(public)
        before_selected = deepcopy(selected)

        post = _project_post_unit_private(m, public, CFG, selected, 1)

        self.assertIsNotNone(post)
        self.assertEqual(post['seeds']['CARROT'], 0)
        self.assertEqual(public, before_public)
        self.assertEqual(selected, before_selected)

    def test_next_turn_seed_need_stays_ahead_of_land_after_partial_plant(self):
        public = observation()
        selected = selected_action()
        planned = route()
        before_public = deepcopy(public)
        before_selected = deepcopy(selected)
        before_route = deepcopy(planned)

        result, report = order_early_capital(
            m, public, CFG, selected, planned,
        )

        self.assertTrue(report['changed'])
        self.assertEqual(report['reason'], 'ordered')
        self.assertEqual(result['market'],
                         [['BUY_SEED', 'CARROT', 1], ['BUY_LAND']])
        self.assertEqual(result['farmer'], selected['farmer'])
        self.assertEqual(result['hands'], selected['hands'])
        self.assertEqual(public, before_public)
        self.assertEqual(selected, before_selected)
        self.assertEqual(planned, before_route)


if __name__ == '__main__':
    unittest.main()
