#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Matched current-V5 OFF/ON gate for EOD capacity rescue.

The candidate arm changes exactly one archive member: TITAN-CONFIG.json,
`eod_capacity_rescue: false -> true`.  Runtime/helper bytes stay identical.
Trace hashes provide an engagement screen before any promotion decision.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def treatment_members(members: dict[str, bytes]) -> tuple[dict[str, bytes], dict]:
    if 'TITAN-CONFIG.json' not in members or 'eod_capacity_rescue.py' not in members:
        raise ValueError('Baseline package does not contain the converged EOD rescue feature')
    result = copy.deepcopy(members)
    config = json.loads(result['TITAN-CONFIG.json'])
    if not isinstance(config, dict) or type(config.get('eod_capacity_rescue')) is not bool:
        raise ValueError('Baseline EOD feature must be an exact bool')
    if config['eod_capacity_rescue'] is not False:
        raise ValueError('Baseline EOD feature must remain default OFF')
    config['eod_capacity_rescue'] = True
    result['TITAN-CONFIG.json'] = (json.dumps(config, indent=2) + '\n').encode()
    changed = [name for name in sorted(members) if members[name] != result[name]]
    if changed != ['TITAN-CONFIG.json']:
        raise AssertionError(f'candidate package changed unexpected members: {changed}')
    identity = {
        'kind': 'member-digest-set',
        'members': {name: digest_bytes(data) for name, data in sorted(result.items())},
    }
    identity['sha256'] = digest_bytes(json.dumps(identity['members'], sort_keys=True,
                                                  separators=(',', ':')).encode())
    return result, identity


def margin(game: dict, seat: int):
    if game.get('status') != 'complete' or game.get('steps') != 719:
        return None
    return game['scores'][seat] - game['scores'][1 - seat]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kg-root', type=Path, required=True)
    parser.add_argument('--engine-dir', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--baseline-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seeds', default='2051966578,1209125501')
    parser.add_argument('--seats', default='0,1')
    parser.add_argument('--opponents', default='apex_v7,arlene_v14')
    parser.add_argument('--rng-seed', type=int, default=20260912)
    parser.add_argument('--action-timeout', type=float, default=1.25)
    parser.add_argument('--startup-timeout', type=float, default=10.0)
    parser.add_argument('--game-timeout', type=float, default=900.0)
    args = parser.parse_args()

    if sys.platform != 'linux':
        parser.error('Use a Linux fleet VM with the existing official-engine cache')
    seeds = [int(x) for x in args.seeds.split(',')]
    seats = [int(x) for x in args.seats.split(',')]
    opponents = args.opponents.split(',')
    if (not seeds or len(seeds) != len(set(seeds)) or not seats
            or len(seats) != len(set(seats)) or not set(seats) <= {0, 1}
            or not opponents or len(opponents) != len(set(opponents))
            or not set(opponents) <= {'apex_v7', 'arlene_v14'}):
        parser.error('Use distinct seeds, seats 0/1, and apex_v7/arlene_v14')
    if any(not math.isfinite(v) or v <= 0 for v in
           (args.action_timeout, args.startup_timeout, args.game_timeout)):
        parser.error('Timeouts must be finite and positive')

    root = args.kg_root.resolve(strict=True)
    engine_dir = args.engine_dir.resolve(strict=True)
    baseline = args.baseline.resolve(strict=True)
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(output)

    shared_path = root / 'cloud-execution-lab/candidates/v5/joint-liquidity-bench/paired.py'
    shared = load(shared_path, 'eod_rescue_shared')
    if shared.digest(baseline) != args.baseline_sha256:
        raise ValueError('Baseline archive differs from declared current package')
    baseline_members = shared.archive_members(baseline)
    candidate_members, candidate_identity = treatment_members(baseline_members)
    baseline_member_identity = {
        name: digest_bytes(data) for name, data in sorted(baseline_members.items())
    }

    output_parent = output.parent.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix='eod-rescue-snapshot-', dir=output_parent) as temporary:
        snapshot_stage = Path(temporary) / 'kg'
        harness = shared.snapshot_harness(root, snapshot_stage, opponents)
        output.mkdir(parents=False, exist_ok=False)
        snapshot_root = output / '.harness-snapshot'
        snapshot_stage.rename(snapshot_root)

    evaluator_path = snapshot_root / shared.EVALUATOR
    loader = snapshot_root / '20260907-offline-agent/evaluate.py'
    evaluator = load(evaluator_path, 'eod_rescue_evaluator')
    pack = load(snapshot_root / 'cloud-pack/pack.py', 'eod_rescue_pack')
    bridge = load(snapshot_root / shared.BANK / 'reference_policies.py', 'eod_rescue_bank')
    engine_hashes = evaluator.verify_sources(engine_dir)

    runtime = {}
    opponent_receipts = {}
    for opponent in opponents:
        runtime[opponent] = output / 'opponents' / opponent
        receipt = bridge.prepare(opponent, snapshot_root, runtime[opponent])
        if receipt.get('support_files') != harness['opponent_support_sha256']:
            raise ValueError(f'opponent support escaped authenticated snapshot: {opponent}')
        opponent_receipts[opponent] = receipt

    cells = []
    for opponent in opponents:
        for seed in seeds:
            for seat in seats:
                cell_id = f'{opponent}-s{seed}-p{seat}'
                games = {}
                order = ['baseline', 'candidate'] if len(cells) % 2 == 0 else ['candidate', 'baseline']
                for label in order:
                    members = baseline_members if label == 'baseline' else candidate_members
                    with tempfile.TemporaryDirectory(prefix=cell_id + '-' + label + '-', dir=output) as temp:
                        directory = Path(temp)
                        payload = directory / 'payload'
                        shared.extract_members(members, payload)
                        adapter = directory / 'adapter.py'
                        pack.write_adapter(adapter, payload / 'main.py')
                        rival = str(runtime[opponent] / 'adapter.py')
                        specs = [str(adapter), rival] if seat == 0 else [rival, str(adapter)]
                        engine, _ = evaluator.get_engine(engine_dir, loader)
                        game = evaluator.play(engine, specs, engine_dir, loader, seed, seat,
                                              args.rng_seed, args.action_timeout,
                                              args.startup_timeout, args.game_timeout)
                    game.update(variant=label, opponent=opponent)
                    games[label] = game
                    shared.write_json(output / f'{cell_id}-{label}.json', game)
                    print(json.dumps({'cell_id': cell_id, 'variant': label,
                                      'status': game['status'], 'steps': game['steps'],
                                      'scores': game['scores'], 'trace_sha256': game['trace_sha256']}),
                          flush=True)
                base_margin = margin(games['baseline'], seat)
                cand_margin = margin(games['candidate'], seat)
                complete = base_margin is not None and cand_margin is not None
                cell = {
                    'cell_id': cell_id, 'opponent': opponent, 'seed': seed, 'seat': seat,
                    'status': 'complete_pair' if complete else 'incomplete_pair',
                    'baseline_margin': base_margin, 'candidate_margin': cand_margin,
                    'margin_delta': cand_margin - base_margin if complete else None,
                    'baseline_scores': games['baseline'].get('scores'),
                    'candidate_scores': games['candidate'].get('scores'),
                    'trace_changed': games['baseline'].get('trace_sha256') != games['candidate'].get('trace_sha256')
                        if complete else None,
                    'baseline_trace_sha256': games['baseline'].get('trace_sha256'),
                    'candidate_trace_sha256': games['candidate'].get('trace_sha256'),
                }
                cells.append(cell)
                shared.write_json(output / f'{cell_id}.json', cell)
                print('PAIR ' + json.dumps(cell), flush=True)

    valid = [c for c in cells if c['status'] == 'complete_pair']
    deltas = [c['margin_delta'] for c in valid]
    summary = {
        'pairs': len(cells), 'complete_pairs': len(valid),
        'trace_changed_pairs': sum(c['trace_changed'] is True for c in valid),
        'improved': sum(d > 0 for d in deltas),
        'unchanged': sum(d == 0 for d in deltas),
        'regressed': sum(d < 0 for d in deltas),
        'mean_margin_delta': sum(deltas) / len(deltas) if deltas else None,
        'cold': bool(valid) and all(c['trace_changed'] is False for c in valid),
    }
    report = {
        'schema': 'titan.v5.eod-capacity-rescue.paired.v1',
        'baseline_sha256': args.baseline_sha256,
        'baseline_member_sha256': baseline_member_identity,
        'candidate_identity': candidate_identity,
        'changed_members': ['TITAN-CONFIG.json'],
        'engine_sha256': engine_hashes,
        'harness': harness,
        'opponent_receipts': opponent_receipts,
        'seeds': seeds, 'seats': seats, 'opponents': opponents,
        'summary': summary, 'cells': cells,
        'interpretation': 'Trace change is the engagement screen; strength promotion requires matched economics and remains separate from merge/default-OFF source convergence.',
    }
    shared.write_json(output / 'REPORT.json', report)
    print('SUMMARY ' + json.dumps(summary), flush=True)
    return int(len(valid) != len(cells))


if __name__ == '__main__':
    raise SystemExit(main())
