# SPDX-License-Identifier: Apache-2.0
"""Focused contracts for complete worker-job valuation and sale binding."""
from copy import deepcopy
from types import SimpleNamespace
import unittest

import mechanics as m
from spatial_tempo import SpatialTempo


class WorkerJobValueContracts(unittest.TestCase):
    def fixture(self):
        tiles = [[None for _ in range(10)] for _ in range(10)]
        tiles[3][4] = {'kind': 'PASTURE', 'animal': 'COW', 'yield_units': 1}
        tiles[0][0] = {'kind': 'PASTURE', 'animal': 'SHEEP', 'yield_units': 1}
        farm = {
            'farmer': [4, 4],
            'hands': [],
            'tiles': tiles,
            'money': 0,
        }
        private = {'shed': {}, 'inventories': [{}], 'seeds': {}}
        market = {
            'inventory': {item: 10000 for item in m.PRODUCTS},
            'params': m.MARKET_PARAMS,
        }
        obs = {
            'step': 0,
            'day': 0,
            'hour': 0,
            'player': 0,
            'farms': [farm, deepcopy(farm)],
            'private': private,
            'market': market,
        }
        route = [
            {'farmer': ['PASS'], 'hands': [], 'market': []}
            for _ in range(24)
        ]
        controller = SimpleNamespace(cur='main', R={'main': route})
        spatial = SpatialTempo(m, pathing=False, tempo=True)
        spatial.configure({})
        return spatial, obs, controller

    def test_complete_job_prefers_cash_per_worker_turn_over_gross_quote(self):
        spatial, obs, controller = self.fixture()
        selected = deepcopy(controller.R['main'][0])

        returned = spatial.transform(obs, selected, controller)

        plan = spatial.plans[0]
        extra = plan['extra']
        self.assertEqual(extra['item'], 'MILK')
        self.assertEqual(extra['quantity'], 1)
        self.assertEqual(extra['projected_sale_value'], 160)
        self.assertEqual(extra['worker_turns'], 4)
        self.assertEqual(extra['valuation'], 'current_quote_cash_per_worker_turn')
        self.assertEqual(extra['sale_step'], 3)
        self.assertEqual(returned['farmer'], ['NORTH'])
        self.assertEqual(controller.R['main'][3]['market'], [])

    def test_sale_binds_only_to_observed_carry_and_drop_turn(self):
        spatial, obs, controller = self.fixture()
        spatial.transform(obs, deepcopy(controller.R['main'][0]), controller)
        sale_step = spatial.plans[0]['extra']['sale_step']
        current = deepcopy(controller.R['main'][sale_step])
        arrived = deepcopy(obs)
        arrived.update(step=sale_step, hour=sale_step)
        arrived['farms'][0]['farmer'] = [4, 4]
        arrived['private']['inventories'][0] = {'MILK': 1}

        offered = spatial._deliver_job_sale(arrived, current, controller)
        self.assertIsNotNone(offered)
        self.assertEqual(offered['farmer'], ['DROP'])
        self.assertEqual(offered['market'], [['SELL', 'MILK', 1]])

        blocked = deepcopy(current)
        blocked['market'] = [['BUY_PRODUCT', 'WHEAT', 1]]
        self.assertIsNone(spatial._deliver_job_sale(arrived, blocked, controller))
        missing = deepcopy(arrived)
        missing['private']['inventories'][0] = {}
        self.assertIsNone(spatial._deliver_job_sale(missing, current, controller))

    def test_position_recovery_invalidates_stale_sale_turn(self):
        spatial, obs, controller = self.fixture()
        spatial.transform(obs, deepcopy(controller.R['main'][0]), controller)
        self.assertIn('sale_step', spatial.plans[0]['extra'])
        moved = deepcopy(obs)
        moved.update(step=1, hour=1)
        moved['farms'][0]['farmer'] = [5, 4]

        spatial._repair_positions(moved, controller)

        self.assertNotIn('sale_step', spatial.plans[0]['extra'])
        self.assertEqual(spatial.plans[0]['extra']['sale_invalidated_at'], 1)


if __name__ == '__main__':
    unittest.main()
