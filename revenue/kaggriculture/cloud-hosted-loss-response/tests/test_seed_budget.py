# SPDX-License-Identifier: Apache-2.0
"""Suffix-budget properties and actual hosted-observation regressions."""
import base64
from copy import deepcopy
import gzip
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

budget_module = load('budget_tests', ROOT / 'seed_budget.py')
entry = load('seed_entry_tests', ROOT / 'seed_main.py')

def row(crop=None):
    return {'farmer': ['PLANT', crop] if crop else ['PASS'], 'hands': [], 'market': []}

class SeedBudgetTests(unittest.TestCase):
    def test_future_compatible_branch_uses_larger_demand(self):
        b = budget_module.SeedBudget({'a': [row(), row(), row('WHEAT')],
                                      'b': [row(), row('WHEAT'), row('WHEAT')]})
        self.assertEqual(b.remaining('WHEAT', 0, 'a'), 2)
        self.assertEqual(b.remaining('WHEAT', 1, 'a'), 1)

    def test_all_worker_requests_count_even_if_potentially_inert(self):
        r = row('WHEAT'); r['hands'] = [['PLANT', 'WHEAT'], ['PLANT', 'CARROT']]
        b = budget_module.SeedBudget({'a': [row(), r]})
        self.assertEqual(b.remaining('WHEAT', 0, 'a'), 2)
        self.assertEqual(b.remaining('CARROT', 0, 'a'), 1)
        self.assertEqual(b.remaining('WHEAT', 1, 'a'), 0)

    def test_slots_other_orders_and_input_unchanged(self):
        b = budget_module.SeedBudget({'a': [row(), row('WHEAT')]})
        action = {'farmer': ['PASS'], 'hands': [['NORTH']],
                  'market': [['SELL', 'WOOL', 3], ['BUY_SEED', 'WHEAT', 9], ['HIRE']]}
        original = deepcopy(action)
        out = b.apply(action, {'WHEAT': 1}, 0, 'a')
        self.assertEqual(action, original)
        self.assertEqual(out['market'], [['SELL', 'WOOL', 3], [], ['HIRE']])
        self.assertEqual(out['hands'], action['hands'])

    def test_current_units_already_consumed_and_future_stock_kept(self):
        b = budget_module.SeedBudget({'a': [row('WHEAT'), row('WHEAT')]})
        a = {'market': [['BUY_SEED', 'WHEAT', 9]]}
        self.assertEqual(b.apply(a, {'WHEAT': 0}, 0, 'a')['market'][0][2], 1)

    def test_never_increases_purchase_when_parent_underfunded(self):
        b = budget_module.SeedBudget({'a': [row()] + [row('WHEAT')] * 10})
        a = {'market': [['BUY_SEED', 'WHEAT', 2]]}
        self.assertEqual(b.apply(a, {'WHEAT': 1}, 0, 'a'), a)

    def test_duplicate_purchase_not_assumed_fulfilled(self):
        b = budget_module.SeedBudget({'a': [row(), row('WHEAT')]})
        a = {'market': [['BUY_SEED', 'WHEAT', 5], ['SELL', 'WOOL', 1], ['BUY_SEED', 'WHEAT', 5]]}
        out = b.apply(a, {'WHEAT': 0}, 0, 'a')
        self.assertEqual(out['market'][0][2], 1)
        self.assertEqual(out['market'][2][2], 1)

    def test_market_limit_and_terminal_suffix(self):
        b = budget_module.SeedBudget({'a': [row()]})
        a = {'market': [['BUY_SEED', 'WHEAT', 2], ['BUY_SEED', 'WHEAT', 4]]}
        self.assertEqual(b.apply(a, {}, 718, 'a', 1)['market'], [[], ['BUY_SEED', 'WHEAT', 4]])

    def test_reduced_fulfilled_purchase_still_covers_all_future_requests(self):
        for demand in range(10):
            b = budget_module.SeedBudget({'a': [row()] + [row('WHEAT')] * demand})
            for stock in range(12):
                for request in range(12):
                    a = {'market': [['BUY_SEED', 'WHEAT', request]]}
                    o = b.apply(a, {'WHEAT': 0}, 0, 'a')['market'][0]
                    retained = o[2] if o else 0
                    self.assertLessEqual(retained, request)
                    self.assertGreaterEqual(stock + retained, min(demand, stock + request))

    def test_actual_public_observation_action_regressions(self):
        cases = json.loads(gzip.decompress(base64.b64decode((ROOT / 'tests/seed-cases.json.gz.b64').read_text())))
        for case in cases:
            with self.subTest(episode=case['episode'], step=case['observation']['step']):
                run = entry.make_agent(ROOT, sell=False)
                calls = []
                original = run.policy.act
                def counted(obs):
                    result = original(obs)
                    calls.append(deepcopy(result))
                    return result
                run.policy.act = counted
                out = run(case['observation'], case['configuration'])
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0], case['recorded_action'])
                changed = deepcopy(calls[0])
                changed['market'][case['slot']] = case['expected_order']
                self.assertEqual(out, changed)
                self.assertEqual(run.budget.events[0]['remaining_request_bound'], case['bound'])
                disabled = entry.make_agent(ROOT, sell=False, enabled=False)
                self.assertEqual(disabled(case['observation'], case['configuration']), calls[0])

if __name__ == '__main__':
    unittest.main()
