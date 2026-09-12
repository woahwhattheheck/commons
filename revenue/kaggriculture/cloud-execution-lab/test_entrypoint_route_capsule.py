# SPDX-License-Identifier: Apache-2.0
"""Keep completed route identity without reviving interrupted runtime state."""
from copy import deepcopy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
if ROOT.name == 'checks':
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
from titan_runtime import deadline

PASS = {'farmer': ['PASS'], 'hands': [], 'market': []}


class ControlledTimer:
    active = None
    cancel_on_exit = False

    def __init__(self, _seconds):
        self.expired = deadline.DeadlineExceeded('controlled outer cancellation')

    def __enter__(self):
        type(self).active = self
        return self

    def __exit__(self, kind, _error, _traceback):
        type(self).active = None
        if kind is None and type(self).cancel_on_exit:
            raise self.expired
        return False


class Instance:
    def __init__(self, route=None, proposed=None):
        self.features = SimpleNamespace(budget_seconds=1.0, reserve_seconds=0.01,
                                        consumer='frozen')
        self.town_procurement_enabled = False
        self._completed_route = route
        self.controller = SimpleNamespace(cur=proposed or route)
        self.selected = None
        self.ready = True
        self.diagnostics = {}

    def act(self, _observation, _configuration=None, *, entry_started=None):
        self.selected = deepcopy(PASS)
        self.diagnostics = {'status': 'completed'}
        return deepcopy(PASS)


class EntrypointRouteCapsuleTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('_route_capsule_entrypoint', ROOT / 'main.py')
        self.entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.entry)
        ControlledTimer.cancel_on_exit = False
        self.timer = patch.object(deadline, '_DeadlineTimer', ControlledTimer)
        self.timer.start()
        self.addCleanup(self.timer.stop)
        self.config = {'episodeSteps': 720}

    @staticmethod
    def obs(step, player=0):
        return {'step': step, 'player': player, 'farms': [{'hands': []}, {'hands': []}],
                'private': {}}

    def cancel(self, instance, step=227):
        self.entry._INSTANCE = instance
        ControlledTimer.cancel_on_exit = True
        self.assertEqual(self.entry.agent(self.obs(step), self.config), PASS)
        ControlledTimer.cancel_on_exit = False
        self.assertIsNone(self.entry._INSTANCE)

    def resume(self, step=228, player=0):
        fresh = Instance()
        with patch.object(self.entry, '_new_instance', return_value=fresh), \
                patch('json.loads', return_value={'town_procurement': False}):
            self.assertEqual(self.entry.agent(self.obs(step, player), self.config), PASS)
        return fresh

    def test_completed_route_survives_whole_call_cancellation(self):
        old = Instance('YARN')
        old._entrypoint_last_step = 226
        self.cancel(old)
        self.assertEqual(self.entry._ROUTE_RECOVERY,
                         {'last_step': 227, 'player': 0, 'route': 'YARN'})
        fresh = self.resume()
        self.assertEqual(fresh._completed_route, 'YARN')
        self.assertIsNot(fresh, old)
        self.assertIsNone(self.entry._ROUTE_RECOVERY)

    def test_uncommitted_controller_choice_is_not_promoted(self):
        old = Instance('YARN', proposed='UNRETURNED_BRANCH')
        self.cancel(old)
        self.assertEqual(self.resume()._completed_route, 'YARN')

    def test_interrupted_current_call_never_relabels_prior_route(self):
        old = Instance('YARN', proposed='UNRETURNED_BRANCH')
        old._entrypoint_last_step = 226
        old._entrypoint_route_receipt = {
            'last_step': 226, 'player': 0, 'route': 'YARN'
        }

        def interrupted(*_args, **_kwargs):
            raise ControlledTimer.active.expired

        old.act = interrupted
        self.entry._INSTANCE = old
        self.assertEqual(self.entry.agent(self.obs(227), self.config), PASS)
        self.assertEqual(self.entry._ROUTE_RECOVERY,
                         {'last_step': 226, 'player': 0, 'route': 'YARN'})
        # Step 227 returned a fallback without a completed route.  At step 228
        # the old step-226 route is now two callbacks stale and must not revive.
        self.assertIsNone(self.resume(228)._completed_route)

    def test_constructor_cancellation_preserves_receipt_without_aging_it(self):
        self.cancel(Instance('YARN'))
        saved = deepcopy(self.entry._ROUTE_RECOVERY)

        def interrupted_constructor(*_args):
            raise ControlledTimer.active.expired

        with patch.object(self.entry, '_new_instance', side_effect=interrupted_constructor), \
                patch('json.loads', return_value={'town_procurement': False}):
            self.assertEqual(self.entry.agent(self.obs(228), self.config), PASS)
        self.assertEqual(self.entry._ROUTE_RECOVERY, saved)
        # Construction at 228 never completed, so a jump to 229 cannot treat
        # the step-227 capsule as if it had completed step 228.
        self.assertIsNone(self.resume(229)._completed_route)

    def test_constructor_cancellation_allows_exact_same_step_retry(self):
        self.cancel(Instance('YARN'))

        def interrupted_constructor(*_args):
            raise ControlledTimer.active.expired

        with patch.object(self.entry, '_new_instance', side_effect=interrupted_constructor), \
                patch('json.loads', return_value={'town_procurement': False}):
            self.assertEqual(self.entry.agent(self.obs(228), self.config), PASS)
        self.assertEqual(self.resume(228)._completed_route, 'YARN')

    def test_new_episode_discards_old_route(self):
        self.cancel(Instance('YARN'))
        self.assertIsNone(self.resume(0)._completed_route)
        self.assertIsNone(self.entry._ROUTE_RECOVERY)

    def test_same_step_zero_retry_retains_step_zero_capsule(self):
        self.cancel(Instance('MAIN'), step=0)
        self.assertEqual(self.resume(0)._completed_route, 'MAIN')

    def test_other_player_rewind_and_step_gap_do_not_reuse_route(self):
        for step, player in ((228, 1), (226, 0), (229, 0)):
            with self.subTest(step=step, player=player):
                self.cancel(Instance('YARN'))
                self.assertIsNone(self.resume(step, player)._completed_route)


if __name__ == '__main__':
    unittest.main(verbosity=2)
