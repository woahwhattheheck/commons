# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from types import SimpleNamespace
import unittest

from spatial_tempo import SpatialTempo, worker_job_projection, worker_job_rank


class FakeMechanics:
    PRODUCTS = {'EGG': {}, 'MILK': {}, 'WHEAT': {}, 'FERTILIZER': {}}
    CROPS = {}
    ANIMALS = {
        'GOOSE': {'product': 'EGG'},
        'COW': {'product': 'MILK'},
    }

    @staticmethod
    def market_price(item, inventory, params):
        if (params or {}).get('floor'):
            return 1
        return {'EGG': 80, 'MILK': 50, 'WHEAT': 1, 'FERTILIZER': 1}[item]


class WorkerJobValueTests(unittest.TestCase):
    def test_projection_prices_complete_round_trip_and_action_budget(self):
        market = {'inventory': {'EGG': 12}, 'params': {}}
        actions = [['EAST'], ['HARVEST'], ['WEST'], ['DROP']]
        p = worker_job_projection(FakeMechanics(), market, 'EGG', 1, actions)
        self.assertEqual(p['receipt'], 80)
        self.assertEqual(p['steps'], 4)
        self.assertEqual(p['travel_steps'], 2)
        self.assertEqual(p['harvest_steps'], 1)
        self.assertEqual(p['deposit_steps'], 1)
        self.assertEqual(p['input_cost'], 0)
        self.assertEqual(p['watering_steps'], 0)
        self.assertEqual(p['value_per_step'], 20.0)
        self.assertEqual(p['basis'], 'current_quote_existing_yield')

    def test_projection_fails_closed_without_sale_value_or_complete_deposit(self):
        floor = {'inventory': {'EGG': 12}, 'params': {'floor': True}}
        self.assertIsNone(worker_job_projection(
            FakeMechanics(), floor, 'EGG', 1,
            [['EAST'], ['HARVEST'], ['WEST'], ['DROP']]))
        market = {'inventory': {'EGG': 12}, 'params': {}}
        self.assertIsNone(worker_job_projection(
            FakeMechanics(), market, 'EGG', 1,
            [['EAST'], ['HARVEST'], ['WEST']]))

    def test_efficiency_rank_prefers_more_value_per_action(self):
        short = {'net_value': 120, 'steps': 3}
        long = {'net_value': 180, 'steps': 6}
        self.assertGreater(worker_job_rank(short), worker_job_rank(long))

    def test_transform_chooses_nearer_higher_efficiency_job_over_gross_value(self):
        tiles = [[None for _ in range(10)] for _ in range(10)]
        tiles[5][4] = {'animal': 'GOOSE', 'yield_units': 1}
        tiles[9][9] = {'animal': 'COW', 'yield_units': 3}
        farm = {'farmer': [4, 4], 'hands': [], 'tiles': tiles}
        other = {'farmer': [4, 4], 'hands': [],
                 'tiles': [[None for _ in range(10)] for _ in range(10)]}
        obs = {
            'step': 0,
            'day': 0,
            'player': 0,
            'farms': [farm, other],
            'private': {'shed': {}, 'inventories': [{}]},
            'market': {
                'inventory': {'EGG': 10, 'MILK': 10, 'WHEAT': 10, 'FERTILIZER': 10},
                'params': {},
            },
        }
        selected = {'farmer': ['PASS'], 'hands': [], 'market': []}
        route = [deepcopy(selected) for _ in range(24)]
        controller = SimpleNamespace(cur='r', R={'r': route})
        tempo = SpatialTempo(FakeMechanics(), pathing=False, tempo=True)

        returned = tempo.transform(obs, deepcopy(selected), controller)

        self.assertEqual(returned['farmer'], ['SOUTH'])
        self.assertEqual(len(tempo.events), 1)
        extra = tempo.events[0]['extra']
        self.assertEqual(extra['tile'], (4, 5))
        self.assertEqual(extra['item'], 'EGG')
        self.assertEqual(extra['projection']['receipt'], 80)
        self.assertEqual(extra['projection']['steps'], 4)
        self.assertEqual(extra['projection']['value_per_step'], 20.0)


if __name__ == '__main__':
    unittest.main()
