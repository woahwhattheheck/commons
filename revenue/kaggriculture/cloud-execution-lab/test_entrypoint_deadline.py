# SPDX-License-Identifier: Apache-2.0
"""Whole-entrypoint deadline containment for canonical TITAN."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parent
if ROOT.name == 'checks':
    ROOT = ROOT.parent


def load_entrypoint():
    name = '_titan_entrypoint_deadline_test'
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, ROOT/'main.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Features:
    budget_seconds = 0.03
    reserve_seconds = 0.005


class _FakeInstance:
    features = _Features()

    def __init__(self, action, *, returned=None, publish_selected=True,
                 diagnostics=None, duration=0.08, error=None):
        self.action = deepcopy(action)
        self.returned = deepcopy(action if returned is None else returned)
        self.publish_selected = publish_selected
        self.selected = None
        self.diagnostics = dict(diagnostics or {})
        self.duration = duration
        self.error = error

    def act(self, _observation, _configuration=None, *, entry_started=None):
        if self.publish_selected:
            self.selected = deepcopy(self.action)
        if self.error is not None:
            raise self.error
        end = time.perf_counter() + self.duration
        while time.perf_counter() < end:
            pass
        return deepcopy(self.returned)


class EntrypointDeadlineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        cls.main = load_entrypoint()
        from titan_runtime import deadline
        cls.deadline = deadline

    def setUp(self):
        self.main._INSTANCE = None
        self.observation = {
            'step': 100,
            'player': 0,
            'farms': [{'hands': [[4, 4]]}, {'hands': []}],
            'private': {},
        }
        self.configuration = {'episodeSteps': 720}
        self.selected = {
            'farmer': ['PASS'],
            'hands': [['PASS']],
            'market': [['SELL', 'CARROT', 1]],
        }

    def test_late_runtime_is_bounded_and_returns_current_selected(self):
        later = deepcopy(self.selected)
        later['market'][0][2] = 2
        fake = _FakeInstance(
            self.selected,
            returned=later,
            diagnostics={'status': 'completed'},
        )
        self.main._INSTANCE = fake
        started = time.perf_counter()
        output = self.main.agent(self.observation, self.configuration)
        elapsed = time.perf_counter() - started
        self.assertEqual(output, self.selected)
        self.assertIsNone(self.main._INSTANCE)
        self.assertLess(elapsed, 0.5)
        self.assertEqual(fake.diagnostics['status'], 'deadline_fallback')
        self.assertEqual(fake.diagnostics['fallback_stage'], 'entrypoint_finalization')
        self.assertTrue(fake.diagnostics['entrypoint_guard'])

    def test_prior_step_selected_is_never_reused(self):
        stale = deepcopy(self.selected)
        stale['market'] = [['SELL', 'MILK', 99]]
        later = deepcopy(self.selected)
        later['market'] = [['SELL', 'EGG', 3]]
        fake = _FakeInstance(self.selected, returned=later, publish_selected=False)
        fake.selected = stale
        self.main._INSTANCE = fake
        output = self.main.agent(self.observation, self.configuration)
        self.assertEqual(
            output,
            {'farmer': ['PASS'], 'hands': [['PASS']], 'market': []},
        )
        self.assertNotEqual(output, stale)
        self.assertIsNone(self.main._INSTANCE)

    def test_normal_runtime_preserves_output_and_instance(self):
        fake = _FakeInstance(self.selected, duration=0)
        self.main._INSTANCE = fake
        output = self.main.agent(self.observation, self.configuration)
        self.assertEqual(output, self.selected)
        self.assertIs(self.main._INSTANCE, fake)
        self.assertNotIn('entrypoint_guard', fake.diagnostics)

    def test_foreign_deadline_sentinel_propagates_by_identity(self):
        foreign = self.deadline.DeadlineExceeded('foreign deadline')
        fake = _FakeInstance(self.selected, error=foreign)
        self.main._INSTANCE = fake
        with self.assertRaises(self.deadline.DeadlineExceeded) as caught:
            self.main.agent(self.observation, self.configuration)
        self.assertIs(caught.exception, foreign)
        self.assertIs(self.main._INSTANCE, fake)

    def test_inner_deadline_receipt_is_retained(self):
        fake = _FakeInstance(
            self.selected,
            diagnostics={
                'status': 'deadline_fallback',
                'fallback_stage': 'selected_transform',
                'elapsed_seconds': 0.02,
            },
        )
        self.main._INSTANCE = fake
        output = self.main.agent(self.observation, self.configuration)
        self.assertEqual(output, self.selected)
        self.assertEqual(fake.diagnostics['fallback_stage'], 'entrypoint_finalization')
        self.assertEqual(fake.diagnostics['inner_fallback_stage'], 'selected_transform')
        self.assertEqual(fake.diagnostics['inner_elapsed_seconds'], 0.02)


if __name__ == '__main__':
    unittest.main()
