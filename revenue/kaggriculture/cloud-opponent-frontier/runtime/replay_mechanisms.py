"""Observe reviewed Barnyard hooks on saved losses, verifying exact action parity.

This is observational replay, not a counterfactual game or a hidden-state model.
The explicitly supplied policy is imported; use only an already reviewed file.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import contextmanager
import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HOOKS = ('_preempt_shift', '_repay_shift', '_weed_repair_action', '_rank_sell_slots')


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@contextmanager
def observe_hooks(module, hooks=HOOKS):
    originals = {name: getattr(module, name) for name in hooks}
    records = {name: {'calls': 0, 'changed': [], 'errors': []} for name in hooks}
    try:
        for name, original in originals.items():
            def watched(*args, _name=name, _original=original, **kwargs):
                obs, action = args[0], args[1]
                before = copy.deepcopy(action)
                record = records[_name]
                record['calls'] += 1
                step = obs.get('step')
                try:
                    result = _original(*args, **kwargs)
                except Exception as error:
                    record['errors'].append({'step': step, 'type': type(error).__name__})
                    raise
                if result != before:
                    record['changed'].append({'step': step, 'before': before,
                                              'after': copy.deepcopy(result)})
                return result
            setattr(module, name, watched)
        yield records
    finally:
        for name, original in originals.items():
            setattr(module, name, original)


def replay_rows(module, rows, seat: int) -> dict:
    if seat not in (0, 1):
        raise ValueError('seat must be 0 or 1')
    matches, total = 0, 0
    mismatches = []
    units, market = Counter(), Counter()
    max_hands = 0
    with observe_hooks(module) as records:
        for number, row in enumerate(rows):
            state = row['before'][seat]
            obs = state.get('observation')
            if not obs and number == 0:
                continue  # The existing engine initialization, not an agent call.
            if not obs or 'private' not in obs or obs.get('player') != seat:
                raise ValueError(f'Missing or wrong-seat observation at trace row {number}')
            action = module.agent(copy.deepcopy(obs))
            expected = state.get('action')
            total += 1
            if action == expected:
                matches += 1
            else:
                mismatches.append({'row': number, 'step': obs.get('step'),
                                   'expected': expected, 'replayed': action})
            for order in [action.get('farmer', []), *action.get('hands', [])]:
                if order:
                    units[order[0]] += 1
            for order in action.get('market', []):
                if order:
                    market[order[0]] += 1
            farms = obs.get('farms', [])
            if len(farms) > seat:
                max_hands = max(max_hands, len(farms[seat].get('hands', [])))
    if not total:
        raise ValueError('No observed agent decisions; empty parity is not evidence')
    return {'seat': seat, 'observations': total, 'exact_action_matches': matches,
            'all_actions_match': matches == total, 'mismatches': mismatches,
            'hooks': records, 'unit_action_requests': dict(units),
            'market_action_requests': dict(market), 'max_observed_hands': max_hands,
            'limits': 'Counts are action requests, not actual yields. Hook replay is observational, not causal ablation.'}


def replay_trace(policy: Path, trace: Path, seat: int) -> dict:
    spec = importlib.util.spec_from_file_location('t07_reviewed_replay', policy)
    if spec is None or spec.loader is None:
        raise ValueError('Cannot import reviewed policy')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    with gzip.open(trace, 'rt', encoding='utf-8') as stream:
        result = replay_rows(module, (json.loads(line) for line in stream), seat)
    result.update(schema='titan.t07.mechanism-replay.v1',
                  policy_sha256=sha256(policy), trace_sha256=sha256(trace))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--trace', type=Path, required=True)
    parser.add_argument('--seat', type=int, choices=(0, 1), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = replay_trace(args.policy.resolve(strict=True), args.trace.resolve(strict=True), args.seat)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + '.tmp')
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')
    temporary.replace(args.output)
    if not result['all_actions_match']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
