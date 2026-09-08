# SPDX-License-Identifier: MIT
"""Clock, source-binding and baseline-before-alternate evaluator boundaries."""
from copy import deepcopy
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import evaluate_frozen_wool_outcomes as outcome


def fixture(changed=True):
    now, cfg = 4, {'episodeSteps': 6, 'turnsPerDay': 24}
    own = {'farmer': ['PASS'], 'hands': [], 'market': [['SELL', 'EGG', 1]]}
    other = {'farmer': ['PASS'], 'hands': [], 'market': []}
    public = {'farms': [{'money': 9}, {'money': 8}], 'market': {'inventory': {'EGG': 0}}, 'town': {}}
    obs = [{**deepcopy(public), 'player': p, 'step': 3, 'day': 0, 'hour': now,
            'private': {'shed': {}, 'inventories': [{}], 'seeds': {}}} for p in (0, 1)]
    rows = [{} for _ in range(6)]
    rows[now] = {'step': 3, 'observations': obs, 'status': ['ACTIVE', 'ACTIVE']}
    terminal = deepcopy(obs)
    for o in terminal: o.update(step=4, hour=5, remainingOverageTime=0)
    rows[now+1] = {'step': now, 'observations': terminal, 'status': ['DONE', 'DONE'],
                   'actions': [deepcopy(own), deepcopy(other)], 'rewards': [9, 8]}
    payload = {'configuration': cfg, 'observation': outcome.normalize(obs[0], 0, now, cfg),
               'selected_action': deepcopy(own)}
    alternate = deepcopy(own)
    if changed: alternate['market'].append([])
    chosen = {'original_action': deepcopy(own), outcome.OBJECTIVE_RESULTS_KEY: {
        'baseline': {'action': deepcopy(own)}, 'cash_pareto': {'action': alternate}}}
    index = {'decision_step': now, 'player': 0, 'source_rows': 6,
             'final_selected_action_sha256': outcome.sha(outcome.encoded(own)),
             'original_scores_evaluation_only': [9, 8], 'identity': 'constructed',
             'runtime_sha256': 'same-own-input', 'source_trace_sha256': 'fixture-only',
             'seed': 100, 'opponent': 'fixture', 'arm': 'control'}
    return index, rows, payload, chosen


def matching_result(rows):
    return {'scores': deepcopy(rows[-1]['rewards']), 'observations': deepcopy(rows[-1]['observations']),
            'status': ['DONE', 'DONE']}


class OutcomeTests(unittest.TestCase):
    def test_normalization_uses_upcoming_decision_and_detaches_input(self):
        values = fixture(); original = deepcopy(values)
        cfg, obs, actions, final = outcome.bind_terminal(*values)
        self.assertEqual(obs[0]['step'], 4)
        self.assertEqual(obs[0]['remainingOverageTime'], 0)
        obs[0]['private']['shed']['EGG'] = 12
        self.assertEqual(values, original)

    def test_wrong_post_action_clock_is_not_replayed(self):
        values = fixture(); values[1][-2]['step'] = 4
        with self.assertRaisesRegex(ValueError, 'misaligned'): outcome.bind_terminal(*values)

    def test_payload_and_source_observation_must_match(self):
        values = fixture(); values[2]['observation']['private']['shed']['EGG'] = 1
        with self.assertRaisesRegex(ValueError, 'differs from raw'): outcome.bind_terminal(*values)

    def test_recorded_and_frozen_actions_must_match(self):
        values = fixture(); values[1][-1]['actions'][0]['market'] = []
        with self.assertRaisesRegex(ValueError, 'recorded action'): outcome.bind_terminal(*values)

    def test_frozen_alternate_cannot_change_workers(self):
        values = fixture(); values[3][outcome.OBJECTIVE_RESULTS_KEY]['cash_pareto']['action']['farmer'] = ['NORTH']
        with self.assertRaisesRegex(ValueError, 'non-market'): outcome.bind_terminal(*values)

    def test_frozen_default_cannot_become_a_different_control(self):
        values = fixture(); values[3][outcome.OBJECTIVE_RESULTS_KEY]['baseline']['action']['market'] = []
        with self.assertRaisesRegex(ValueError, 'unchanged baseline'): outcome.bind_terminal(*values)

    def test_inconsistent_recorded_rewards_fail_before_engine(self):
        values = fixture(); values[0]['original_scores_evaluation_only'][0] += 1
        with patch.object(outcome, 'execute') as execute:
            with self.assertRaisesRegex(ValueError, 'reward records'): outcome.evaluate_record(NS(), *values)
        execute.assert_not_called()

    def test_wrong_baseline_scores_stop_before_alternate(self):
        values = fixture(); result = matching_result(values[1]); result['scores'][0] -= 1
        with patch.object(outcome, 'execute', return_value=result) as execute:
            with self.assertRaisesRegex(ValueError, 'recorded final scores'): outcome.evaluate_record(NS(), *values)
        self.assertEqual(execute.call_count, 1)

    def test_wrong_baseline_state_stops_even_when_scores_match(self):
        values = fixture(); result = matching_result(values[1]); result['observations'][0]['private']['shed']['EGG'] = 1
        with patch.object(outcome, 'execute', return_value=result) as execute:
            with self.assertRaisesRegex(ValueError, 'complete terminal state'): outcome.evaluate_record(NS(), *values)
        self.assertEqual(execute.call_count, 1)

    def test_alternate_is_used_unchanged_after_matching_baseline(self):
        values = fixture(); original = deepcopy(values)
        baseline = matching_result(values[1]); alternative = deepcopy(baseline); alternative['scores'] = [8, 10]
        with patch.object(outcome, 'execute', side_effect=[baseline, alternative]) as execute:
            report = outcome.evaluate_record(NS(), *values)
        self.assertEqual(execute.call_count, 2)
        self.assertEqual(execute.call_args_list[1].args[3][0], values[3][outcome.OBJECTIVE_RESULTS_KEY]['cash_pareto']['action'])
        self.assertEqual(report['margin_delta'], -3)
        self.assertEqual((report['verdict_before'], report['verdict_after']), ('W', 'L'))
        self.assertEqual(values, original)

    def test_identical_selected_action_reuses_matching_baseline(self):
        values = fixture(changed=False)
        with patch.object(outcome, 'execute', return_value=matching_result(values[1])) as execute:
            report = outcome.evaluate_record(NS(), *values)
        self.assertEqual(execute.call_count, 1)
        self.assertFalse(report['selected_action_changed'])
        self.assertEqual(report['margin_delta'], 0)

    def test_frozen_file_bytes_cannot_be_substituted(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'choices.json'; path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                outcome.checked_file(path, outcome.CHOICES_SHA256)

    def test_duplicate_payloads_cannot_hide_different_rival_consequences(self):
        values = fixture(changed=False)
        with patch.object(outcome, 'execute', return_value=matching_result(values[1])):
            report = outcome.evaluate_record(NS(), *values)
        altered = deepcopy(report); altered['counterfactual_own_rival'][0] += 1
        with self.assertRaisesRegex(ValueError, 'differing actual-rival'):
            outcome.summarize([report, altered])


if __name__ == '__main__':
    unittest.main(verbosity=2)
