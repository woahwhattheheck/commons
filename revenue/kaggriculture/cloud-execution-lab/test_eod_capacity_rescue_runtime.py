# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

import build_integrated
import eod_capacity_rescue
import main as titan_main
import titan_runtime

LAB = Path(__file__).resolve().parent


class _FakeFeatures:
    def __init__(self, **values):
        self.consumer = values.get('consumer', 'frozen')
        self.terminal_route = values.get('terminal_route', False)
        self.fourth_quadrant = values.get('fourth_quadrant', False)
        self.overflow_safe_drop = values.get('overflow_safe_drop', False)
        self.eod_capacity_rescue = values.get('eod_capacity_rescue', False)
        self.budget_seconds = values.get('budget_seconds', 1.0)


class _FakeTitanAgent:
    def __init__(self, *args, **kwargs):
        self.diagnostics = {'status': 'completed'}
        self.consumer = object()
        self.history = None
        self.spatial = None
        self.selected = None

    def _initialize(self):
        return None

    def act(self, observation, configuration=None, *, entry_started=None):
        return {'farmer': ['PASS'], 'hands': [], 'market': []}

    def _early_capital_selected(self, obs, cfg, selected):
        return deepcopy(selected)

    def _market_pressure_selected(self, obs, cfg, selected):
        return selected

    def _feed_stock_selected(self, obs, cfg, selected):
        return selected


class EODCapacityRescueRuntimeTest(unittest.TestCase):
    def _new(self, *, eod=False, overflow=False, load=None):
        if load is None:
            def load(name, path, *, cache=False):
                raise AssertionError(f'unexpected helper load: {name} {path} {cache}')
        with (mock.patch.object(titan_runtime, 'TitanAgent', _FakeTitanAgent),
              mock.patch.object(titan_runtime, 'Features', _FakeFeatures),
              mock.patch.object(titan_runtime, 'load', load)):
            return titan_main._new_instance(
                LAB,
                {
                    'consumer': 'frozen',
                    'terminal_route': False,
                    'fourth_quadrant': False,
                    'overflow_safe_drop': overflow,
                    'eod_capacity_rescue': eod,
                },
            )

    @staticmethod
    def _selected():
        return {'farmer': ['PASS'], 'hands': [], 'market': []}

    @staticmethod
    def _observation(step=23):
        return {'player': 0, 'step': step}

    @staticmethod
    def _configuration():
        return {'episodeSteps': 720}

    @staticmethod
    def _module(fn):
        return types.SimpleNamespace(apply_native_eod_capacity_rescue=fn)

    def test_feature_is_strict_default_off_bool(self):
        self.assertFalse(titan_runtime.Features().eod_capacity_rescue)
        self.assertTrue(titan_runtime.Features(eod_capacity_rescue=True).eod_capacity_rescue)
        for poison in (0, 1, 'true', None):
            with self.subTest(poison=poison):
                with self.assertRaises(TypeError):
                    titan_runtime.Features(eod_capacity_rescue=poison)
        config = json.loads((LAB / 'TITAN-CONFIG.json').read_text())
        self.assertIs(config['eod_capacity_rescue'], False)

    def test_release_maps_helper_focused_and_runtime_tests(self):
        mapping = build_integrated.source_files()
        self.assertEqual(mapping['eod_capacity_rescue.py'], 'eod_capacity_rescue.py')
        self.assertEqual(mapping['checks/test_eod_capacity_rescue.py'],
                         'test_eod_capacity_rescue.py')
        self.assertEqual(mapping['checks/test_eod_capacity_rescue_runtime.py'],
                         'test_eod_capacity_rescue_runtime.py')

    def test_default_off_never_imports_or_calls_eod_helper(self):
        poison = types.ModuleType('eod_capacity_rescue')
        with mock.patch.dict(sys.modules, {'eod_capacity_rescue': poison}):
            instance = self._new(eod=False, overflow=False)
            selected = self._selected()
            returned = instance._early_capital_selected(
                self._observation(), self._configuration(), selected)
        self.assertEqual(returned, selected)
        self.assertNotIn('eod_capacity_rescue', instance.diagnostics)
        self.assertEqual(instance._finalizer_checkpoint['stage'], 'market_pressure')

    def test_enabled_eod_rewrites_and_checkpoints_returned_action(self):
        calls = []

        def apply(action, observation, configuration, *, enabled=False):
            calls.append((deepcopy(action), enabled))
            changed = deepcopy(action)
            changed['market'].append(['SELL', 'CARROT', 1])
            return changed, {'changed': True, 'reason': 'test'}

        with mock.patch.dict(sys.modules, {'eod_capacity_rescue': self._module(apply)}):
            instance = self._new(eod=True)
            returned = instance._early_capital_selected(
                self._observation(), self._configuration(), self._selected())
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0][1])
        self.assertEqual(returned['market'], [['SELL', 'CARROT', 1]])
        self.assertTrue(instance.diagnostics['eod_capacity_rescue']['changed'])
        self.assertEqual(instance._finalizer_checkpoint['stage'], 'eod_capacity_rescue')
        self.assertEqual(instance._finalizer_checkpoint['action'], returned)

    def test_eod_consumes_post_overflow_action_once(self):
        call_log = []
        overflow_inputs = []
        eod_inputs = []
        eod_outputs = []

        class Overflow:
            @staticmethod
            def transform(action, observation, configuration):
                call_log.append('overflow')
                overflow_inputs.append(deepcopy(action))
                changed = deepcopy(action)
                changed['farmer'] = ['PLACE', 'CARROT', 1]
                return changed, {'changed': True}

        def apply(action, observation, configuration, *, enabled=False):
            call_log.append('eod')
            eod_inputs.append(deepcopy(action))
            changed = deepcopy(action)
            changed['market'].append(['SELL', 'CARROT', 1])
            eod_outputs.append(deepcopy(changed))
            return changed, {'changed': True}

        def load(name, path, *, cache=False):
            self.assertEqual(name, '_titan_overflow_safe_drop')
            return Overflow

        with mock.patch.dict(sys.modules, {'eod_capacity_rescue': self._module(apply)}):
            instance = self._new(eod=True, overflow=True, load=load)
            returned = instance._early_capital_selected(
                self._observation(), self._configuration(), self._selected())
        self.assertEqual(call_log, ['overflow', 'eod'])
        self.assertEqual(len(overflow_inputs), 1)
        self.assertEqual(len(eod_inputs), 1)
        self.assertEqual(eod_inputs[0]['farmer'], ['PLACE', 'CARROT', 1])
        self.assertEqual(len(eod_outputs), 1)
        self.assertEqual(returned, eod_outputs[0])
        self.assertEqual(returned['farmer'], ['PLACE', 'CARROT', 1])
        self.assertEqual(returned['market'], [['SELL', 'CARROT', 1]])
        self.assertEqual(instance._finalizer_checkpoint['stage'], 'eod_capacity_rescue')

    def test_post_overflow_sell_blocks_real_eod_rewrite_without_reentry(self):
        call_log = []
        overflow_calls = []

        class Overflow:
            @staticmethod
            def transform(action, observation, configuration):
                call_log.append('overflow')
                overflow_calls.append(deepcopy(action))
                changed = deepcopy(action)
                changed['market'].append(['SELL', 'MILK', 1])
                return changed, {'changed': True}

        def real_apply(action, observation, configuration, *, enabled=False):
            call_log.append('eod')
            return eod_capacity_rescue.apply_native_eod_capacity_rescue(
                action, observation, configuration, enabled=enabled
            )

        def load(name, path, *, cache=False):
            self.assertEqual(name, '_titan_overflow_safe_drop')
            return Overflow

        farm = {
            'farmer': [0, 0],
            'hands': [],
            'tiles': [[None for _ in range(10)] for _ in range(10)],
            'money': 100,
        }
        observation = {
            'step': 23,
            'player': 0,
            'farms': [deepcopy(farm), deepcopy(farm)],
            'private': {
                'inventories': [{'MILK': 5}],
                'shed': {'MILK': 100},
                'seeds': {},
            },
            'market': {'prices': {'MILK': 4}},
        }
        configuration = {
            'boardSize': 10,
            'turnsPerDay': 24,
            'shedCapacity': 100,
            'maxMarketOrdersPerTurn': 10,
            'episodeSteps': 720,
            'townShopSellInterval': 4,
            'townCenterSellInterval': 24,
        }

        with mock.patch.dict(sys.modules, {
            'eod_capacity_rescue': self._module(real_apply),
        }):
            instance = self._new(eod=True, overflow=True, load=load)
            returned = instance._early_capital_selected(
                observation, configuration, self._selected())

        self.assertEqual(call_log, ['overflow', 'eod'])
        self.assertEqual(len(overflow_calls), 1)
        self.assertEqual(returned['market'], [['SELL', 'MILK', 1]])
        self.assertFalse(instance.diagnostics['eod_capacity_rescue']['changed'])
        self.assertEqual(
            instance.diagnostics['eod_capacity_rescue']['reason'],
            'market_stock_or_unknown',
        )
        self.assertEqual(instance._finalizer_checkpoint['stage'], 'eod_capacity_rescue')
        self.assertEqual(instance._finalizer_checkpoint['action'], returned)

    def test_incomplete_path_suppresses_eod_helper(self):
        calls = []

        def forbidden(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError('incomplete actions must not enter EOD rescue')

        with mock.patch.dict(sys.modules, {'eod_capacity_rescue': self._module(forbidden)}):
            instance = self._new(eod=True)
            instance.diagnostics['status'] = 'deadline_fallback'
            selected = self._selected()
            returned = instance._early_capital_selected(
                self._observation(), self._configuration(), selected)
        self.assertEqual(returned, selected)
        self.assertEqual(calls, [])
        self.assertNotIn('eod_capacity_rescue', instance.diagnostics)
        self.assertEqual(instance._finalizer_checkpoint['stage'], 'early_capital')


if __name__ == '__main__':
    unittest.main()
