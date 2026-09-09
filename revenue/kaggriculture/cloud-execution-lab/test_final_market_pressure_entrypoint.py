# SPDX-License-Identifier: Apache-2.0
"""Composition contracts for the canonical final market-pressure boundary."""
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from unittest.mock import patch
import sys
import unittest

import main


class FakeFeatures:
    def __init__(self, market_pressure=False, fourth_quadrant=False, **kwargs):
        self.market_pressure = market_pressure
        self.fourth_quadrant = fourth_quadrant
        self.terminal_history = bool(kwargs.get('terminal_history', False))
        self.crop_release = bool(kwargs.get('crop_release', False))
        self.budget_seconds = float(kwargs.get('budget_seconds', 1.0))


class FakeHistory:
    fill_result = None

    def __init__(self):
        self.remembered = []
        self.diagnostics = {'remembered': 0}

    def remember(self, obs, cfg, returned, post):
        self.remembered.append(deepcopy(returned))
        self.diagnostics = {'remembered': len(self.remembered)}


class FakeTitanAgent:
    def __init__(self, features, fourth_quadrant_admission=None):
        self.features = features
        self.diagnostics = {}
        self.calls = []
        self.spatial = None
        self.quadrant = None
        self._quadrant_admission = fourth_quadrant_admission
        self.history = FakeHistory()

    def _market_pressure_selected(self, obs, cfg, selected):
        if not self.features.market_pressure:
            return selected
        self.calls.append('pressure')
        result = deepcopy(selected)
        result['trace'] = result.get('trace', []) + ['pressure']
        self.diagnostics['market_pressure'] = {
            'enabled': True,
            'changed': result != selected,
        }
        return result

    def _selected_snapshot(self, obs, returned=None):
        return {'snapshot': True}

    def _feed_stock_selected(self, obs, cfg, selected):
        self.calls.append('feed')
        result = deepcopy(selected)
        result['trace'] = result.get('trace', []) + ['feed']
        return result

    def _early_capital_selected(self, obs, cfg, selected):
        self.calls.append('capital')
        result = deepcopy(selected)
        result['trace'] = result.get('trace', []) + ['capital']
        return result


class FinalMarketPressureEntrypointTests(unittest.TestCase):
    def make_agent(self, enabled=True):
        runtime = ModuleType('titan_runtime')
        runtime.Features = FakeFeatures
        runtime.TitanAgent = FakeTitanAgent
        runtime.load = lambda *args, **kwargs: self.fail('optional admission loaded')
        with patch.dict(sys.modules, {'titan_runtime': runtime}):
            return main._new_instance(Path('.'), {
                'market_pressure': enabled,
                'fourth_quadrant': False,
            })

    def test_early_stage_is_identity_and_pressure_is_last_committed_transform(self):
        agent = self.make_agent()
        selected = {'farmer': ['PASS'], 'hands': [], 'market': [], 'trace': []}
        self.assertIs(agent._market_pressure_selected({}, {}, selected), selected)
        self.assertEqual(agent.calls, [])

        agent.diagnostics['status'] = 'completed'
        result = agent._finish_production({}, selected, {})
        self.assertEqual(result['trace'], ['feed', 'capital', 'pressure'])
        self.assertEqual(agent.calls, ['feed', 'capital', 'pressure'])
        self.assertEqual(agent.history.remembered, [result])
        self.assertEqual(agent.diagnostics['market_pressure'], {
            'enabled': True,
            'changed': True,
        })
        self.assertIs(agent._market_pressure_selected({}, {}, selected), selected)

    def test_deadline_fallback_does_not_start_optional_pressure(self):
        agent = self.make_agent()
        agent.diagnostics['status'] = 'deadline_fallback'
        result = agent._finish_production({}, {'trace': []}, {})
        self.assertEqual(result['trace'], ['feed', 'capital'])
        self.assertEqual(agent.calls, ['feed', 'capital'])
        self.assertEqual(agent.history.remembered, [result])
        self.assertNotIn('market_pressure', agent.diagnostics)

    def test_disabled_feature_remains_identity_at_final_boundary(self):
        agent = self.make_agent(enabled=False)
        agent.diagnostics['status'] = 'completed'
        result = agent._finish_production({}, {'trace': []}, {})
        self.assertEqual(result['trace'], ['feed', 'capital'])
        self.assertEqual(agent.calls, ['feed', 'capital'])
        self.assertEqual(agent.history.remembered, [result])
        self.assertNotIn('market_pressure', agent.diagnostics)


if __name__ == '__main__':
    unittest.main(verbosity=2)
