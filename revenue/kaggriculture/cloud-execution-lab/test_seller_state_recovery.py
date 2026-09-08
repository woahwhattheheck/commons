# SPDX-License-Identifier: Apache-2.0
"""Completed frozen-seller state survives only selected-action cancellation."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import titan_runtime as T
import test_ordered_selected_sell as seller_tests

ROOT = Path(__file__).resolve().parent
ROWS = []
FIELDS = ('planned', 'pending', 'previous', 'observed_harvests')


class SellerStateRecovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seller_tests.OrderedSelectedSellTests.setUpClass()
        cls.helper = seller_tests.OrderedSelectedSellTests()

    def obs(self, step):
        observation, configuration, _, _ = self.helper.fixture(step=step)
        return observation, configuration

    def complete_checkpoint(self, agent, step=100):
        observation, configuration = self.obs(step)
        marker = {
            'planned': {'MILK': [(step + 3, 2)]},
            'pending': {'MILK': 2},
            'previous': copy.deepcopy(observation),
            'observed_harvests': {'CARROT': [(step, 3)]},
        }

        def complete(obs, cfg, selected):
            for name, value in marker.items():
                setattr(agent.consumer, name, copy.deepcopy(value))
            return copy.deepcopy(selected)

        with patch.object(agent, 'transform_selected', side_effect=complete):
            output = agent.act(observation, configuration)
        self.assertEqual(agent.diagnostics['status'], 'completed')
        self.assertEqual(output, agent.selected)
        return marker

    def interrupt(self, agent, observation, configuration, *, production=False, foreign=None):
        original_timer = T.deadline._DeadlineTimer
        timers = []

        def timer(seconds):
            value = original_timer(seconds)
            timers.append(value)
            return value

        def stop(*args, **kwargs):
            if foreign is not None:
                raise foreign
            raise timers[-1].expired

        target = agent.production if production else agent
        method = 'act' if production else 'transform_selected'
        with patch.object(T.deadline, '_DeadlineTimer', side_effect=timer), \
             patch.object(target, method, side_effect=stop):
            return agent.act(observation, configuration)

    def test_selected_fallback_restores_completed_fields_and_skipped_observation(self):
        agent = T.TitanAgent()
        marker = self.complete_checkpoint(agent)
        old_consumer = agent.consumer
        observation, configuration = self.obs(101)
        original_input = copy.deepcopy(observation)
        output = self.interrupt(agent, observation, configuration)
        self.assertEqual(output, agent.selected)
        self.assertFalse(agent.ready)
        self.assertEqual(agent._seller_recovery_observation, original_input)
        observation['market']['inventory']['MILK'] += 1
        agent._initialize()
        self.assertIsNot(agent.consumer, old_consumer)
        self.assertEqual(agent.consumer.planned, marker['planned'])
        self.assertEqual(agent.consumer.pending, marker['pending'])
        self.assertEqual(agent.consumer.observed_harvests, marker['observed_harvests'])
        self.assertEqual(agent.consumer.previous, original_input)
        self.assertIsNone(agent._seller_recovery_observation)
        ROWS.append({'case': 'selected_fallback', 'restored_fields': list(FIELDS),
                     'observer_advanced_step': 101})

    def test_completed_checkpoint_is_detached_from_later_consumer_mutation(self):
        agent = T.TitanAgent()
        marker = self.complete_checkpoint(agent)
        checkpoint = copy.deepcopy(agent._completed_seller_state)
        agent.consumer.planned['MILK'].append((199, 99))
        agent.consumer.pending['MILK'] = 99
        agent.consumer.observed_harvests['CARROT'].append((199, 99))
        self.assertEqual(agent._completed_seller_state, checkpoint)
        self.assertEqual(checkpoint['planned'], marker['planned'])
        self.assertEqual(checkpoint['pending'], marker['pending'])

    def test_production_cancellation_does_not_restore_old_seller_state(self):
        agent = T.TitanAgent()
        self.complete_checkpoint(agent)
        observation, configuration = self.obs(101)
        output = self.interrupt(agent, observation, configuration, production=True)
        self.assertEqual(output, T.deadline.legal_pass(observation))
        self.assertFalse(agent.ready)
        self.assertIsNone(agent._seller_recovery_observation)
        agent._initialize()
        self.assertEqual(agent.consumer.planned, {})
        self.assertEqual(agent.consumer.pending, {})
        self.assertIsNone(agent.consumer.previous)
        self.assertEqual(agent.consumer.observed_harvests, {})
        ROWS.append({'case': 'unreturned_production', 'restored': False})

    def test_first_selected_cancellation_without_checkpoint_stays_fresh(self):
        agent = T.TitanAgent()
        agent._initialize()
        observation, configuration = self.obs(1)
        output = self.interrupt(agent, observation, configuration)
        self.assertEqual(output, agent.selected)
        self.assertIsNone(agent._completed_seller_state)
        self.assertIsNone(agent._seller_recovery_observation)
        agent._initialize()
        self.assertEqual(agent.consumer.planned, {})
        self.assertIsNone(agent.consumer.previous)

    def test_foreign_deadline_identity_propagates_without_recovery_marker(self):
        agent = T.TitanAgent()
        self.complete_checkpoint(agent)
        observation, configuration = self.obs(101)
        foreign = T.deadline.DeadlineExceeded('foreign')
        with self.assertRaises(T.deadline.DeadlineExceeded) as caught:
            self.interrupt(agent, observation, configuration, foreign=foreign)
        self.assertIs(caught.exception, foreign)
        self.assertIsNone(agent._seller_recovery_observation)

    def test_normal_completion_replaces_checkpoint_and_clears_marker(self):
        agent = T.TitanAgent()
        first = self.complete_checkpoint(agent, 100)
        agent._seller_recovery_observation = {'sentinel': True}
        second = self.complete_checkpoint(agent, 102)
        self.assertIsNone(agent._seller_recovery_observation)
        self.assertNotEqual(first['previous']['step'], second['previous']['step'])
        self.assertEqual(agent._completed_seller_state['planned'], second['planned'])
        self.assertEqual(agent._completed_seller_state['previous'], second['previous'])


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(SellerStateRecovery))
    output = ROOT / 'runtime/integrated-selected/SELLER-STATE-RECOVERY-TESTS.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'tests': result.testsRun,
                                  'passed': result.wasSuccessful(),
                                  'cases': ROWS,
                                  'new_games': 0}, indent=2) + '\n')
    raise SystemExit(not result.wasSuccessful())
