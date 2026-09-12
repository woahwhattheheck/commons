#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
SOURCE_ROOT = HERE.parents[2]
S8_RUNNER = SOURCE_ROOT / 'candidates/v4/repairs/gameplay/s8-egg-care/run_s8_field.py'
DEFAULT_SEEDS = (2026091201, 2026091207, 2026091213, 2026091219)


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def paired_first_change(base_rows: Path, candidate_rows: Path):
    base = read_json(base_rows)
    candidate = read_json(candidate_rows)
    for left, right in zip(base, candidate):
        if left['step'] != right['step']:
            return min(left['step'], right['step'])
        if left['own_action_sha256'] != right['own_action_sha256']:
            return left['step']
    if len(base) != len(candidate):
        return min(len(base), len(candidate))
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-main-git-blob', required=True)
    parser.add_argument('--expected-config-git-blob', required=True)
    parser.add_argument('--seeds', default=','.join(map(str, DEFAULT_SEEDS)))
    args = parser.parse_args()

    runtime = args.runtime.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    candidate_runtime = output / 'materialized-wf1'
    materializer = load(HERE / 'materialize.py', 'wf1_v5_materializer')
    materialization = materializer.materialize(
        runtime, candidate_runtime,
        expected_main_blob=args.expected_main_git_blob,
        expected_config_blob=args.expected_config_git_blob,
    )
    runner = load(S8_RUNNER, 'wf1_v5_native_runner')
    entry = candidate_runtime / 'wf1_v5_entry.py'
    seeds = tuple(int(value) for value in args.seeds.split(',') if value.strip())
    cells = []

    for seed in seeds:
        for seat in (0, 1):
            key = f'seed-{seed}-seat-{seat}'
            base_dir = output / key / 'base'
            candidate_dir = output / key / 'wf1'
            baseline = runner.play(runtime, seed, seat, base_dir,
                                   opponent=runtime, passive=False)
            candidate = runner.play(candidate_runtime, seed, seat, candidate_dir,
                                    opponent=runtime, passive=False,
                                    entry=str(entry) + '::agent')
            complete = (baseline.get('status') == 'complete'
                        and candidate.get('status') == 'complete')
            delta = None
            if complete:
                delta = {
                    'own': candidate['scores'][seat] - baseline['scores'][seat],
                    'rival': candidate['scores'][1-seat] - baseline['scores'][1-seat],
                    'margin': candidate['margin'] - baseline['margin'],
                }
            cells.append({
                'seed': seed,
                'seat': seat,
                'complete': complete,
                'base': {key: baseline.get(key) for key in
                         ('status', 'steps', 'scores', 'margin', 'failure',
                          'trace_sha256', 'action_sha256', 'world_sha256')},
                'wf1': {key: candidate.get(key) for key in
                        ('status', 'steps', 'scores', 'margin', 'failure',
                         'trace_sha256', 'action_sha256', 'world_sha256')},
                'first_action_change_step': paired_first_change(
                    base_dir / 'rows.json', candidate_dir / 'rows.json'),
                'delta': delta,
            })

    complete = [cell for cell in cells if cell['complete']]
    margins = [cell['delta']['margin'] for cell in complete]
    own = [cell['delta']['own'] for cell in complete]
    rival = [cell['delta']['rival'] for cell in complete]
    result = {
        'schema': 'titan.v5.wf1-current-native-field/v1',
        'materialization': materialization,
        'seeds': list(seeds),
        'cells': cells,
        'summary': {
            'requested_cells': len(cells),
            'complete_cells': len(complete),
            'game_failures': len(cells) - len(complete),
            'changed_action_cells': sum(cell['first_action_change_step'] is not None for cell in complete),
            'positive_margin_cells': sum(value > 0 for value in margins),
            'zero_margin_cells': sum(value == 0 for value in margins),
            'negative_margin_cells': sum(value < 0 for value in margins),
            'mean_margin_delta': statistics.mean(margins) if margins else None,
            'median_margin_delta': statistics.median(margins) if margins else None,
            'mean_own_delta': statistics.mean(own) if own else None,
            'mean_rival_delta': statistics.mean(rival) if rival else None,
        },
    }
    (output / 'WF1-V5-FIELD-RESULT.json').write_text(
        json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    print(json.dumps(result['summary'], sort_keys=True, allow_nan=False))
    return int(len(complete) != len(cells))


if __name__ == '__main__':
    raise SystemExit(main())
