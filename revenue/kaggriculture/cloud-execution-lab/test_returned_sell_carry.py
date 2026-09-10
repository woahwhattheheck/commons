# SPDX-License-Identifier: Apache-2.0
"""Returned-action binding for FrozenSelected SELL carry."""
from copy import deepcopy
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys
import unittest

ROOT = Path(__file__).resolve().parent
if ROOT.name == 'checks':
    ROOT = ROOT.parent


def load_entrypoint():
    name = '_titan_returned_sell_carry_test'
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, ROOT/'main.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def state(planned=None, pending=None):
    return {
        'planned': deepcopy(planned or {}),
        'pending': dict(pending or {}),
        'previous': {'step': 17},
        'observed_harvests': {},
    }


def action(*orders):
    return {'farmer': ['PASS'], 'hands': [], 'market': list(orders)}


class ReturnedSellCarryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = load_entrypoint()

    def reconcile(self, before, after, authored, returned, *, step=18, limit=10):
        return self.main._reconcile_returned_sell_carry(
            before, after, authored, returned, step, limit)

    def test_carries_only_late_removed_due_units(self):
        before = state({'WHEAT': [(18, 5), (22, 7)]})
        after = state({'WHEAT': [(22, 7)]})
        got, report = self.reconcile(
            before, after, action(['SELL', 'WHEAT', 8]),
            action(['SELL', 'WHEAT', 4]))
        self.assertEqual(got['planned']['WHEAT'], [(19, 4), (22, 7)])
        self.assertEqual(got['pending']['WHEAT'], 4)
        self.assertEqual(report['items']['WHEAT'], {
            'due_before': 5,
            'removed_after_guards': 4,
            'already_carried': 0,
            'carried_to_next_turn': 4,
        })
        self.assertTrue(report['changed'])

    def test_never_carries_baseline_units_beyond_due_plan(self):
        before = state({'WHEAT': [(18, 2)]})
        got, report = self.reconcile(
            before, state(), action(['SELL', 'WHEAT', 9]),
            action([], ['BUY_PRODUCT', 'FERTILIZER', 1]))
        self.assertEqual(got['planned']['WHEAT'], [(19, 2)])
        self.assertEqual(got['pending']['WHEAT'], 2)
        self.assertEqual(report['items']['WHEAT']['removed_after_guards'], 9)

    def test_raw_prefix_not_whole_queue_controls_carry(self):
        before = state({'WHEAT': [(18, 3)]})
        authored = action(*([[]]*9), ['SELL', 'WHEAT', 3])
        returned = action(*([[]]*10), ['SELL', 'WHEAT', 3])
        got, report = self.reconcile(before, state(), authored, returned)
        self.assertEqual(self.main._sell_prefix_totals(authored, 10), {'WHEAT': 3})
        self.assertEqual(self.main._sell_prefix_totals(returned, 10), {})
        self.assertEqual(got['planned']['WHEAT'], [(19, 3)])
        self.assertTrue(report['changed'])

    def test_existing_due_carry_is_not_duplicated(self):
        before = state({'WHEAT': [(18, 5)]})
        after = state({'WHEAT': [(18, 4)]}, {'WHEAT': 4})
        got, report = self.reconcile(
            before, after, action(['SELL', 'WHEAT', 8]),
            action(['SELL', 'WHEAT', 4]))
        self.assertEqual(got, after)
        self.assertEqual(report['items']['WHEAT']['already_carried'], 4)
        self.assertFalse(report['changed'])

    def test_full_return_and_opportunistic_sell_create_no_obligation(self):
        before = state({'WHEAT': [(18, 5)]})
        after = state()
        got, report = self.reconcile(
            before, after, action(['SELL', 'WHEAT', 5]),
            action(['SELL', 'WHEAT', 5], ['SELL', 'EGG', 9]))
        self.assertEqual(got, after)
        self.assertFalse(report['changed'])

    def test_inputs_are_immutable_and_future_rows_coalesce(self):
        before = state({'WHEAT': [(18, 5), (19, 2)]})
        after = state({'WHEAT': [(19, 1), (19, 1)]}, {'WHEAT': 1})
        frozen = deepcopy(after)
        got, report = self.reconcile(
            before, after, action(['SELL', 'WHEAT', 5]),
            action(['SELL', 'WHEAT', 2]))
        self.assertEqual(after, frozen)
        self.assertEqual(got['planned']['WHEAT'], [(19, 5)])
        self.assertEqual(got['pending']['WHEAT'], 4)
        self.assertTrue(report['changed'])

    def test_wrapper_updates_live_and_recovery_state_after_finalizer(self):
        main = self.main
        fake = ModuleType('titan_runtime')

        class Features:
            def __init__(self, **values):
                self.consumer = values.get('consumer', 'frozen')
                self.fourth_quadrant = values.get('fourth_quadrant', False)

        class TitanAgent:
            def __init__(self, features, **_kwargs):
                self.features = features
                self.ready = True
                self.consumer = SimpleNamespace(
                    planned={'WHEAT': [(18, 5)]}, pending={},
                    previous={'step': 17}, observed_harvests={})
                self._completed_seller_state = state({'WHEAT': [(18, 5)]})
                self.diagnostics = {}

            @staticmethod
            def _seller_state(consumer):
                return state(consumer.planned, consumer.pending)

            def act(self, observation, configuration=None, *, entry_started=None):
                del entry_started
                self.consumer.planned = {}
                self.consumer.pending = {'WHEAT': 0}
                self._completed_seller_state = state({}, {'WHEAT': 0})
                self.diagnostics = {'status': 'completed'}
                return self._finish_production(
                    observation, action(['SELL', 'WHEAT', 8]), configuration)

            def _finish_production(self, _obs, _returned, _cfg=None):
                return action(['SELL', 'WHEAT', 4])

            def _market_pressure_selected(self, _obs, _cfg, selected):
                return selected

            def _early_capital_selected(self, _obs, _cfg, selected):
                return selected

        fake.TitanAgent = TitanAgent
        fake.Features = Features
        fake.load = lambda *_args, **_kwargs: None
        prior = sys.modules.get('titan_runtime')
        sys.modules['titan_runtime'] = fake
        try:
            instance = main._new_instance(ROOT, {'consumer': 'frozen'})
            returned = instance.act({'step': 18}, {'maxMarketOrdersPerTurn': 10})
        finally:
            if prior is None:
                sys.modules.pop('titan_runtime', None)
            else:
                sys.modules['titan_runtime'] = prior
        self.assertEqual(returned, action(['SELL', 'WHEAT', 4]))
        self.assertEqual(instance.consumer.planned, {'WHEAT': [(19, 4)]})
        self.assertEqual(instance.consumer.pending, {'WHEAT': 4})
        self.assertEqual(instance._completed_seller_state['planned'],
                         {'WHEAT': [(19, 4)]})
        self.assertTrue(instance.diagnostics['returned_sell_carry']['changed'])


if __name__ == '__main__':
    unittest.main()
