# SPDX-License-Identifier: Apache-2.0
"""Regression coverage for same-step replay in thin integrated entrypoints."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent


class _FakeAgent:
    def __init__(self, identity, failures):
        self.identity = identity
        self.failures = failures
        self.calls = []

    def act(self, observation, configuration=None):
        step = observation.get('step')
        if step is None:
            step = (int(observation['day'])
                    * int((configuration or {}).get('turnsPerDay', 24))
                    + int(observation['hour']))
        step = int(step)
        self.calls.append(step)
        if step in self.failures:
            self.failures.remove(step)
            raise RuntimeError('synthetic act failure')
        return {'instance': self.identity, 'step': step}


def _load(filename):
    name = '_test_' + filename.replace('.', '_')
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IntegratedWrapperReplayTest(unittest.TestCase):
    def _exercise(self, filename):
        module = _load(filename)
        created = []
        failures = set()

        def make_agent():
            instance = _FakeAgent(len(created) + 1, failures)
            created.append(instance)
            return instance

        module.make_agent = make_agent

        self.assertEqual(module.agent({'step': 0}), {'instance': 1, 'step': 0})
        self.assertEqual(module.agent({'step': 0}), {'instance': 1, 'step': 0})
        self.assertEqual(len(created), 1)

        self.assertEqual(module.agent({'step': 2}), {'instance': 1, 'step': 2})
        self.assertEqual(module.agent({'step': 2}), {'instance': 1, 'step': 2})
        self.assertEqual(len(created), 1)

        # A strict public-step rewind is a new/reordered stream boundary.
        self.assertEqual(module.agent({'step': 1}), {'instance': 2, 'step': 1})
        self.assertEqual(len(created), 2)
        self.assertEqual(
            module.agent({'day': 0, 'hour': 1}, {'turnsPerDay': 24}),
            {'instance': 2, 'step': 1},
        )
        self.assertEqual(len(created), 2)

        # The rewind marker is published only after a complete return. A failed
        # rebuilt instance must not become reusable on the next same-step retry.
        failures.add(0)
        with self.assertRaisesRegex(RuntimeError, 'synthetic act failure'):
            module.agent({'step': 0})
        self.assertEqual(module._LAST_STEP, 1)
        self.assertEqual(len(created), 3)
        self.assertEqual(module.agent({'step': 0}), {'instance': 4, 'step': 0})
        self.assertEqual(len(created), 4)

    def test_integrated_main_replay_and_reset(self):
        self._exercise('integrated_main.py')

    def test_integrated_parent_replay_and_reset(self):
        self._exercise('integrated_parent.py')


if __name__ == '__main__':
    unittest.main()
