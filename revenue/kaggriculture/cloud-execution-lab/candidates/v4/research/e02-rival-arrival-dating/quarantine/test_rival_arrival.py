"""Focused E02 public rival-arrival regressions."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

import scheduler as scheduling
import selected_sell_core as selected_core
from seller_snapshot import seller_public_observation as base_seller_public_observation

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    'test_rival_arrival_runtime', HERE/'reference/titan-current/rival_arrival.py')
e02 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e02)


def farm(*, actor=(4, 4), hands=(), tile_at=None):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    if tile_at is not None:
        x, y, tile = tile_at
        tiles[y][x] = copy.deepcopy(tile)
    return {
        'tiles': tiles,
        'farmer': list(actor),
        'hands': [list(pos) for pos in hands],
        'money': 12345,  # Public but intentionally not retained by the seller snapshot.
    }


def observation(step, rival_farm):
    return {
        'step': step,
        'player': 0,
        'farms': [farm(), rival_farm],
    }


class RivalArrivalTests(unittest.TestCase):
    def scheduler_with_previous(self, old):
        agent = scheduling.SellScheduler()
        agent.previous = e02.seller_public_observation(old)
        return agent

    def test_snapshot_retains_only_public_rival_actor_geometry(self):
        rival = farm(actor=(1, 2), hands=((3, 4),),
                     tile_at=(1, 2, {'kind': 'PLANT', 'crop': 'TOMATO', 'yield_units': 2}))
        obs = observation(17, rival)
        snap = e02.seller_public_observation(obs)
        self.assertEqual(snap['step'], 17)
        self.assertEqual(snap['farms'][1]['farmer'], [1, 2])
        self.assertEqual(snap['farms'][1]['hands'], [[3, 4]])
        self.assertNotIn('money', snap['farms'][1])
        rival['farmer'][0] = 9
        self.assertEqual(snap['farms'][1]['farmer'], [1, 2], 'snapshot must detach live public state')

    def test_close_harvest_dates_next_legal_drop_and_sale(self):
        old_tile = {'kind': 'PLANT', 'crop': 'TOMATO', 'yield_units': 2}
        new_tile = {'kind': 'PLANT', 'crop': 'TOMATO', 'yield_units': 0}
        old = observation(17, farm(actor=(4, 3), tile_at=(4, 3, old_tile)))
        new = observation(18, farm(actor=(4, 3), tile_at=(4, 3, new_tile)))
        agent = self.scheduler_with_previous(old)
        e02.observe(agent, new)
        supply = e02.rival_supply(agent, new, 'TOMATO')
        self.assertEqual(int(supply), 2)
        self.assertEqual(len(supply.hypotheses), 1)
        event = supply.hypotheses[0]
        self.assertEqual((event['earliest'], event['latest']), (19, 24))
        self.assertTrue(event['certain'])

    def test_shed_adjacent_and_remote_harvest_bounds(self):
        old_tile = {'kind': 'PLANT', 'crop': 'TOMATO', 'yield_units': 2}
        new_tile = {'kind': 'PLANT', 'crop': 'TOMATO', 'yield_units': 0}
        cases = [((4, 4), 18), ((0, 0), 24)]
        for pos, expected in cases:
            with self.subTest(position=pos):
                old = observation(17, farm(actor=pos, tile_at=(*pos, old_tile)))
                new = observation(18, farm(actor=pos, tile_at=(*pos, new_tile)))
                agent = self.scheduler_with_previous(old)
                e02.observe(agent, new)
                event = e02.rival_supply(agent, new, 'TOMATO').hypotheses[0]
                self.assertEqual(event['earliest'], expected)
                self.assertEqual(event['latest'], 24)

    def test_decay_without_public_actor_is_not_hidden_cargo(self):
        old_tile = {'kind': 'PLANT', 'crop': 'WHEAT', 'yield_units': 2}
        weed = {'kind': 'WEED'}
        old = observation(17, farm(actor=(4, 4), tile_at=(0, 0, old_tile)))
        new = observation(18, farm(actor=(4, 4), tile_at=(0, 0, weed)))
        agent = self.scheduler_with_previous(old)
        e02.observe(agent, new)
        self.assertFalse(e02.rival_supply(agent, new, 'WHEAT').hypotheses)
        self.assertEqual(int(e02.rival_supply(agent, new, 'WHEAT')), 0)

    def test_nonongoing_removal_keeps_zero_vs_harvest_ambiguity(self):
        old_tile = {'kind': 'PLANT', 'crop': 'CARROT', 'yield_units': 2}
        old = observation(17, farm(actor=(1, 1), tile_at=(1, 1, old_tile)))
        new = observation(18, farm(actor=(1, 1)))
        agent = self.scheduler_with_previous(old)
        e02.observe(agent, new)
        event = e02.rival_supply(agent, new, 'CARROT').hypotheses[0]
        self.assertFalse(event['certain'], 'DIG and HARVEST are both public-compatible')
        self.assertEqual(event['quantity'], 2)
        self.assertEqual(event['earliest'], 24)

    def test_end_of_day_animal_escape_is_ambiguous_but_arrived_by_reset(self):
        cow = {'kind': 'PASTURE', 'animal': 'COW', 'yield_units': 4}
        bare = {'kind': 'PASTURE'}
        old = observation(23, farm(actor=(2, 2), tile_at=(2, 2, cow)))
        new = observation(24, farm(actor=(4, 4), tile_at=(2, 2, bare)))
        agent = self.scheduler_with_previous(old)
        e02.observe(agent, new)
        event = e02.rival_supply(agent, new, 'MILK').hypotheses[0]
        self.assertFalse(event['certain'])
        self.assertEqual((event['earliest'], event['latest']), (24, 24))
        self.assertEqual(event['quantity'], 4)

    def test_carrot_quantity_only_vs_dated_arrival_ranking_inversion(self):
        path = selected_core.MarketPath('CARROT', 9700, None,
                                        ['PET_CAFE', 'PET_CAFE'], {}, 18, 24)
        plans = {
            18: ((18, 2),),
            22: ((22, 2),),
            24: ((24, 2),),
        }
        immediate = {step: path.score(plan, 2, 12, 'paired')[0]
                     for step, plan in plans.items()}
        dated = {step: path.score(plan, 2, ((24, 12),), 'paired')[0]
                 for step, plan in plans.items()}
        self.assertEqual(immediate, {18: -577, 22: -579, 24: -579})
        self.assertEqual(dated, {18: -580, 22: -578, 24: -580})
        self.assertEqual(max(immediate, key=immediate.get), 18)
        self.assertEqual(max(dated, key=dated.get), 22)

    def test_timed_optimizer_can_select_dated_plan_while_retaining_scalar_stress(self):
        supply = e02.RivalSupply(12, ({
            'observed_step': 18, 'quantity': 12,
            'earliest': 24, 'latest': 24,
            'certain': False, 'tile': [0, 0],
        },), visible=0, recent=12)
        plan, info = e02.selected_optimize_lot(
            item='CARROT', quantity=2, inventory=9700, params=None,
            shops=['PET_CAFE', 'PET_CAFE'], config={}, now=18,
            dates=[18, 22, 24], reference=((18, 2),),
            rival_quantity=supply, last=718)
        self.assertEqual(dict(plan).get(22), 2)
        self.assertIn('public_harvest_earliest', info['scenarios'])
        self.assertIn('observed_paired', info['stress_scenarios'])
        self.assertLess(info['stress_scenarios']['observed_paired']['relative_value'],
                        info['stress_scenarios']['observed_paired']['reference_relative_value'])
        self.assertEqual(info['rival_arrival_hypotheses'][0]['earliest'], 24)

    def test_no_timing_delegates_exactly_to_inherited_optimizer(self):
        kwargs = dict(item='CARROT', quantity=2, inventory=9700, params=None,
                      shops=['PET_CAFE', 'PET_CAFE'], config={}, now=18,
                      dates=[18, 22, 24], reference=((18, 2),),
                      rival_quantity=e02.RivalSupply(12), last=718)
        inherited = e02._ORIGINAL_SELECTED_OPTIMIZE(**kwargs)
        wrapped = e02.selected_optimize_lot(**kwargs)
        self.assertEqual(wrapped, inherited)


if __name__ == '__main__':
    unittest.main(verbosity=2)
