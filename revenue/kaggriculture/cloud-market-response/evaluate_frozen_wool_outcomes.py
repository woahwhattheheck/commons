# SPDX-License-Identifier: MIT
"""Evaluation-only final transitions AFTER PR10215's choices were frozen.

Reads original rival state/actions solely in this downstream evaluator. No
history inference, scenario generation, solver, actor, or complete game runs.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace as NS
import zipfile

# The immutable PR10215 JSON uses this legacy field for objective results.
OBJECTIVE_RESULTS_KEY = 'choices'

CHOICES_SHA256 = 'bc5076379363ac998e2b7bb69cf3e1b936c6ddaca4711b95f66856014c36fa88'
ORIGINAL_SHA256 = '2f8566ed9cd7cd04d342216c9eb5922f3d8bd361ffd952994439e10e9771907a'
INPUT_SHA256 = 'b64a2363365b4e6711c08c38b3398bc44466994ef3d4d75da2a35be9d8488568'
ENGINE_SHA256 = {
    'kaggriculture.py': 'bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e',
    'utils.py': '537b627b11784d424147ef57ebb0369b039bf83c9f891e81f10486b1f552334b',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def checked_file(path, expected):
    data = Path(path).read_bytes()
    require(sha(data) == expected, 'Frozen file identity mismatch: ' + str(path))
    return data


def normalize(raw, player, now, cfg):
    obs = deepcopy(raw)
    require(obs['player'] == player, 'Recorded observation player mismatch')
    require(obs['day'] * cfg['turnsPerDay'] + obs['hour'] == now, 'Recorded public clock mismatch')
    obs['step'] = now
    obs['remainingOverageTime'] = 0
    return obs


def bind_terminal(index, rows, payload, chosen):
    """Bind raw post-action records to their actual upcoming decision inputs."""
    cfg = deepcopy(payload['configuration'])
    now, player = index['decision_step'], index['player']
    require(cfg.get('seed') is None, 'Runtime-derived configuration must remain seed-free')
    require(now == cfg['episodeSteps'] - 2, 'Only the final actionable transition is supported')
    require((now + 1) % cfg['turnsPerDay'] != 0, 'This retained boundary must not call a daily random refresh')
    require(len(rows) == now + 2 == index['source_rows'], 'Recorded transition count mismatch')
    pre, final = rows[now], rows[now + 1]
    require(pre['step'] == now - 1 and final['step'] == now, 'Post-action trace clock is misaligned')
    require(pre['status'] == ['ACTIVE', 'ACTIVE'] and final['status'] == ['DONE', 'DONE'],
            'Retained final transition must be active then complete')
    observations = [normalize(pre['observations'][i], i, now, cfg) for i in (0, 1)]
    for name in ('farms', 'market', 'town'):
        require(observations[0][name] == observations[1][name], 'Public state differs between recorded seats')
    require(observations[player] == payload['observation'], 'Frozen decision observation differs from raw pre-state')
    original_action = payload['selected_action']
    require(final['actions'][player] == original_action == chosen['original_action'],
            'Frozen own action differs from original recorded action')
    require(sha(encoded(original_action)) == index['final_selected_action_sha256'], 'Original action digest mismatch')
    require(chosen[OBJECTIVE_RESULTS_KEY]['baseline']['action'] == original_action, 'Frozen default is not the unchanged baseline')
    for label in ('baseline', 'cash_pareto'):
        action = chosen[OBJECTIVE_RESULTS_KEY][label]['action']
        require({k: v for k, v in action.items() if k != 'market'} ==
                {k: v for k, v in original_action.items() if k != 'market'},
                'Frozen comparison must preserve every non-market action field')
    require(final['rewards'] == index['original_scores_evaluation_only'], 'Original reward records disagree')
    return cfg, observations, deepcopy(final['actions']), final


def execute(engine, cfg, observations, actions):
    """One complete native terminal step from real pre-state, never an actor call."""
    shared = {key: deepcopy(observations[0][key]) for key in ('farms', 'market', 'town')}
    state = []
    for i in (0, 1):
        obs = deepcopy(observations[i]); obs.update(shared)
        state.append(NS(observation=NS(**obs), action=deepcopy(actions[i]), status='ACTIVE', reward=0))
    env = NS(configuration=NS(**cfg), done=False, info={})
    engine.interpreter(state, env)
    require(all(s.status == 'DONE' for s in state), 'Native terminal step did not finish')
    return {'scores': [s.reward for s in state],
            'observations': [deepcopy(vars(s.observation)) for s in state],
            'status': [s.status for s in state]}


def verdict(own, rival):
    return 'W' if own > rival else 'L' if own < rival else 'T'


def evaluate_record(engine, index, rows, payload, chosen):
    cfg, observations, actions, recorded = bind_terminal(index, rows, payload, chosen)
    baseline = execute(engine, cfg, observations, actions)
    require(baseline['scores'] == recorded['rewards'], 'Native baseline does not reproduce recorded final scores')
    require(baseline['observations'] == recorded['observations'], 'Native baseline does not reproduce complete terminal state')
    player = index['player']; other = 1 - player
    alternative = deepcopy(chosen[OBJECTIVE_RESULTS_KEY]['cash_pareto']['action'])
    changed = alternative != actions[player]
    evaluated = baseline
    if changed:
        changed_actions = deepcopy(actions); changed_actions[player] = alternative
        evaluated = execute(engine, cfg, observations, changed_actions)
    own0, rival0 = baseline['scores'][player], baseline['scores'][other]
    own1, rival1 = evaluated['scores'][player], evaluated['scores'][other]
    return {
        'source_identity': index['identity'], 'runtime_sha256': index['runtime_sha256'],
        'source_trace_sha256': index['source_trace_sha256'],
        'seed_evaluation_only': index['seed'], 'player': player,
        'opponent_evaluation_only': index['opponent'], 'original_arm_evaluation_only': index['arm'],
        'selected_action_changed': changed,
        'original_action': deepcopy(actions[player]), 'frozen_action': alternative,
        'actual_rival_action_evaluation_only': deepcopy(actions[other]),
        'baseline_own_rival': [own0, rival0], 'counterfactual_own_rival': [own1, rival1],
        'own_cash_delta': own1 - own0, 'rival_cash_delta': rival1 - rival0,
        'margin_delta': (own1 - rival1) - (own0 - rival0),
        'verdict_before': verdict(own0, rival0), 'verdict_after': verdict(own1, rival1),
        'baseline_complete_state_matches': True,
        'native_terminal_transitions': 1 + int(changed),
        'counterfactual_terminal_state': evaluated['observations'],
    }


def summarize(reports):
    unique = {}
    for report in reports:
        key = report['runtime_sha256']
        pair = (report['baseline_own_rival'], report['counterfactual_own_rival'])
        if key in unique:
            require(pair == (unique[key]['baseline_own_rival'], unique[key]['counterfactual_own_rival']),
                    'Same own payload has differing actual-rival consequences; do not collapse it')
        else:
            unique[key] = report
    def summary(rows):
        return {
            'records': len(rows), 'changed_actions': sum(r['selected_action_changed'] for r in rows),
            'before_wtl': dict(Counter(r['verdict_before'] for r in rows)),
            'after_wtl': dict(Counter(r['verdict_after'] for r in rows)),
            'verdict_transitions': dict(Counter(r['verdict_before'] + '->' + r['verdict_after'] for r in rows)),
            'margin_positive': sum(r['margin_delta'] > 0 for r in rows),
            'margin_zero': sum(r['margin_delta'] == 0 for r in rows),
            'margin_negative': sum(r['margin_delta'] < 0 for r in rows),
            'sum_own_cash_delta': sum(r['own_cash_delta'] for r in rows),
            'sum_rival_cash_delta': sum(r['rival_cash_delta'] for r in rows),
            'sum_margin_delta': sum(r['margin_delta'] for r in rows),
            'min_margin_delta': min(r['margin_delta'] for r in rows),
            'max_margin_delta': max(r['margin_delta'] for r in rows),
        }
    return {
        'source_record_accounting': summary(reports),
        'unique_runtime_payload_accounting': summary(list(unique.values())),
        'original_development_seeds': sorted({r['seed_evaluation_only'] for r in reports}),
        'source_opponents': sorted({r['opponent_evaluation_only'] for r in reports}),
        'native_terminal_transitions': sum(r['native_terminal_transitions'] for r in reports),
        'complete_baselines_reconciled': len(reports),
        'new_full_games': 0, 'new_game_seeds': 0, 'selector_calls': 0, 'production_calls': 0,
        'meaning': 'Evaluation-only terminal counterfactuals of frozen decisions on already-exposed development traces. Payloads/seat mirrors/arms are not independent games or held evidence.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--choices', required=True, type=Path)
    parser.add_argument('--original-archive', required=True, type=Path)
    parser.add_argument('--input-archive', required=True, type=Path)
    parser.add_argument('--engine-loader', required=True, type=Path)
    parser.add_argument('--engine-dir', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    choices_data = checked_file(args.choices, CHOICES_SHA256)
    checked_file(args.original_archive, ORIGINAL_SHA256)
    checked_file(args.input_archive, INPUT_SHA256)
    for name, expected in ENGINE_SHA256.items(): checked_file(args.engine_dir/name, expected)
    require((args.engine_dir/'kaggriculture.json').is_file(), 'Existing engine specification required; no downloads')
    spec = importlib.util.spec_from_file_location('_wool_outcome_engine_loader', args.engine_loader)
    loader = importlib.util.module_from_spec(spec); spec.loader.exec_module(loader)
    engine, hashes = loader.get_engine(args.engine_dir)
    choices = json.loads(choices_data)['reports']
    by_payload = {r['input_sha256']: r for r in choices}
    require(len(by_payload) == len(choices) == 10, 'Frozen choice set must contain ten distinct inputs')
    reports = []
    with zipfile.ZipFile(args.original_archive) as original, zipfile.ZipFile(args.input_archive) as inputs:
        manifest = json.loads(original.read('MANIFEST.json'))['members']
        require(set(original.namelist()) == set(manifest) | {'MANIFEST.json'}, 'Original archive membership differs')
        for name, member in manifest.items():
            data = original.read(name)
            require(len(data) == member['size'] and sha(data) == member['sha256'], 'Original archive member mismatch: ' + name)
        index = json.loads(inputs.read('index.json'))
        require(index['actor_input'] is False and index['source_archive_sha256'] == ORIGINAL_SHA256,
                'Source index is not bound to the original evaluation archive')
        for record in index['records']:
            compressed = inputs.read(record['runtime_member']); raw = gzip.decompress(compressed)
            require(sha(compressed) == record['runtime_gzip_sha256'] and sha(raw) == record['runtime_sha256'], 'Runtime payload mismatch')
            payload = json.loads(raw)
            require(payload['schema'] == 'titan.public-own-history.v1', 'Unexpected runtime payload schema')
            source = original.read(record['source_trace_member']); plain = gzip.decompress(source)
            require(sha(source) == record['source_trace_sha256'] and sha(plain) == record['source_transition_sha256'], 'Original trace identity mismatch')
            rows = [json.loads(line) for line in plain.splitlines()]
            reports.append(evaluate_record(engine, record, rows, payload, by_payload[record['runtime_sha256']]))
    summary = summarize(reports)
    document = {'schema': 'titan.frozen-wool-actual-outcomes.v1',
        'frozen_choices_sha256': CHOICES_SHA256, 'original_archive_sha256': ORIGINAL_SHA256,
        'input_archive_sha256': INPUT_SHA256, 'engine_sha256': hashes,
        'source_sha256': sha(Path(__file__).read_bytes()),
        'summary': summary, 'reports': reports, 'actual_rival_data_scope': 'downstream evaluation only'}
    args.output.write_text(json.dumps(document, indent=2, allow_nan=False) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
