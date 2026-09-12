# SPDX-License-Identifier: Apache-2.0
"""Regression contracts for the run-only regime scheduler entrypoint."""
import unittest

import regime_scheduler as rs


class _FakeScheduler:
    created = 0

    def __init__(self, mode='candidate'):
        type(self).created += 1
        self.identity = type(self).created
        self.calls = []

    def act(self, obs, configuration=None):
        self.calls.append((int(obs.get('step', 0)), dict(configuration or {})))
        return {'identity': self.identity, 'calls': len(self.calls)}


class RegimeSchedulerEntrypointTests(unittest.TestCase):
    def setUp(self):
        self.original_scheduler = rs.RegimeSellScheduler
        self.original_instance = rs._INSTANCE
        _FakeScheduler.created = 0
        rs.RegimeSellScheduler = _FakeScheduler
        rs._INSTANCE = None

    def tearDown(self):
        rs.RegimeSellScheduler = self.original_scheduler
        rs._INSTANCE = self.original_instance

    def test_exact_step_zero_replay_reuses_completed_wrapper(self):
        first_output = rs.agent({'step': 0}, {'tag': 'first'})
        first = rs._INSTANCE
        second_output = rs.agent({'step': 0}, {'tag': 'retry'})

        self.assertIs(rs._INSTANCE, first)
        self.assertEqual(first_output['identity'], second_output['identity'])
        self.assertEqual(first.calls, [(0, {'tag': 'first'}), (0, {'tag': 'retry'})])
        self.assertEqual(first._regime_entrypoint_last_step, 0)
        self.assertEqual(_FakeScheduler.created, 1)

    def test_later_step_to_zero_reconstructs_for_new_match(self):
        rs.agent({'step': 0})
        first = rs._INSTANCE
        rs.agent({'step': 1})
        self.assertIs(rs._INSTANCE, first)
        self.assertEqual(first._regime_entrypoint_last_step, 1)

        output = rs.agent({'step': 0})
        second = rs._INSTANCE
        self.assertIsNot(second, first)
        self.assertEqual(output['identity'], second.identity)
        self.assertEqual(first.calls, [(0, {}), (1, {})])
        self.assertEqual(second.calls, [(0, {})])
        self.assertEqual(second._regime_entrypoint_last_step, 0)
        self.assertEqual(_FakeScheduler.created, 2)


if __name__ == '__main__':
    unittest.main()
