# SPDX-License-Identifier: Apache-2.0
"""Contracts for inherited-intent priority over the complete SELL target set."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import frozen_selected
from frozen_selected import FrozenSelected
from scheduler import PRODUCTS, m, ordered_targets


def _fixture(now=100):
    baseline_item = PRODUCTS[0]
    preferred_item = PRODUCTS[-1]
    farm = {
        'tiles': [[None] * 10 for _ in range(10)],
        'farmer': [4, 4],
        'hands': [],
        'money': 100000,
        'hires_today': 0,
        'unlocked_quadrants': ['NW'],
    }
    private = {
        'shed': {baseline_item: 3, preferred_item: 4},
        'seeds': {},
        'inventories': [{}],
    }
    obs = {
        'step': now,
        'player': 0,
        'farms': [farm, deepcopy(farm)],
        'private': private,
        'market': {
            'inventory': {product: 10000 for product in m.PRODUCTS},
            'prices': {product: 10 for product in m.PRODUCTS},
        },
        'town': {'unlocked_shops': []},
    }
    route = [
        {'farmer': ['PASS'], 'hands': [], 'market': []}
        for _ in range(720)
    ]
    base = deepcopy(route[now])
    base['market'] = [['SELL', baseline_item, 1]]
    return obs, route, base, baseline_item, preferred_item


def _consumer(route, preferred_item):
    bot = FrozenSelected.__new__(FrozenSelected)
    bot.controller = SimpleNamespace(R={'test': route}, cur='test')
    bot.mode = 'candidate'
    bot.pending = {preferred_item: 0}
    bot.planned = {}
    bot.previous = None
    bot.observed_harvests = {}
    bot.diagnostics = {}
    bot.joint_producer_busy = True
    return bot


def _equal_optimizer(**kwargs):
    item = kwargs['item']
    quantity = int(kwargs['quantity'])
    now = int(kwargs['now'])
    plan = ((now, quantity),)
    return plan, {
        'item': item,
        'quantity': quantity,
        'reference': list(kwargs['reference']),
        'plan': list(plan),
        'worst_relative_gain': 1.0,
        'accepted': True,
        'acceptance_score': 1.0,
        'forced_feasibility': False,
        'feasible': True,
        'scenarios': {
            'no_rival': {
                'reference_relative_value': 0.0,
                'relative_value': 1.0,
            },
        },
    }


class OrderedTargetContracts(unittest.TestCase):
    def test_pending_then_baseline_then_unseen_products(self):
        first, second, third, fourth = PRODUCTS[:4]
        shed = {first: 1, second: 2, third: 3, fourth: 4}
        pending = {fourth: 0, second: 0}
        baseline = {third: 7, fourth: 9, first: 1}

        result = ordered_targets(shed, pending, baseline)

        self.assertEqual(list(result), [fourth, second, third, first])
        self.assertEqual(result, {
            fourth: 4,
            second: 2,
            third: 3,
            first: 1,
        })

    def test_membership_matches_complete_v2_stock_domain(self):
        shed = {product: index + 1 for index, product in enumerate(PRODUCTS)}
        shed.update({'WHEAT': 99, 'FERTILIZER': 99, 'UNKNOWN': 99})
        pending = {PRODUCTS[-1]: 0, 'UNKNOWN': 1}
        baseline = {PRODUCTS[1]: 1, 'WHEAT': 1}

        result = ordered_targets(shed, pending, baseline)
        predecessor = {
            product: max(0, int(shed.get(product, 0)))
            for product in PRODUCTS
            if shed.get(product, 0) > 0
        }

        self.assertEqual(set(result), set(predecessor))
        self.assertEqual(result, predecessor)
        self.assertNotEqual(list(result), list(predecessor))

    def test_zero_pending_key_keeps_first_seen_priority_when_stock_arrives(self):
        first, last = PRODUCTS[0], PRODUCTS[-1]
        result = ordered_targets(
            {first: 2, last: 3},
            {last: 0},
            {first: 2},
        )
        self.assertEqual(list(result), [last, first])

    def test_inputs_are_not_mutated(self):
        first, second = PRODUCTS[:2]
        shed = {first: 3, second: 4}
        pending = {second: 0}
        baseline = {first: 1}
        before = deepcopy((shed, pending, baseline))

        ordered_targets(shed, pending, baseline)

        self.assertEqual((shed, pending, baseline), before)

    def test_both_production_paths_consume_the_priority_helper(self):
        here = Path(__file__).resolve().parent
        root = here if (here / 'scheduler.py').is_file() else here.parent
        needle = 'targets=ordered_targets(shed,self.pending,baseline_q)'
        predecessor = (
            'targets={p:max(0,int(shed.get(p,0))) '
            'for p in PRODUCTS if shed.get(p,0)>0}'
        )
        for name in ('scheduler.py', 'frozen_selected.py'):
            source = (root / name).read_text(encoding='utf-8')
            self.assertEqual(source.count(needle), 1, name)
            self.assertNotIn(predecessor, source, name)


class FrozenSelectedPriorityIntegration(unittest.TestCase):
    def test_equal_rank_selects_prior_intent_without_narrowing_stock(self):
        obs, route, base, baseline_item, preferred_item = _fixture()
        original_obs = deepcopy(obs)
        original_base = deepcopy(base)
        bot = _consumer(route, preferred_item)

        with (
            patch.object(bot, 'cash_reserve', return_value=0),
            patch.object(bot, 'receipt_profile', return_value=lambda _plan: True),
            patch.object(bot, 'rival_supply', return_value=0),
            patch(
                'frozen_selected.funded_minimum_now',
                side_effect=lambda *_args, **_kwargs: (0, {'admitted': True}),
            ),
            patch('frozen_selected.optimize_lot', side_effect=_equal_optimizer),
            patch(
                'frozen_selected.fund_same_turn_acquisition',
                side_effect=lambda orders, *_args, **_kwargs: (deepcopy(orders), None),
            ),
        ):
            returned = bot.transform(obs, {}, base)

        self.assertEqual(bot.diagnostics['chosen']['item'], preferred_item)
        self.assertEqual(returned['market'][0], ['SELL', baseline_item, 1])
        self.assertIn(['SELL', preferred_item, 4], returned['market'])
        self.assertEqual(
            set(ordered_targets(obs['private']['shed'], {preferred_item: 0},
                                {baseline_item: 1})),
            {baseline_item, preferred_item},
        )
        self.assertEqual(obs, original_obs)
        self.assertEqual(base, original_base)


if __name__ == '__main__':
    unittest.main()
