# SPDX-License-Identifier: Apache-2.0
"""Offline native-entrypoint parity and alternating timing, one game per process.

Authenticates the complete checked native package before cloning. Changes only
mechanics.py in an explicit scratch tree; no config, route, archive or release
mutation. No observation filtering, actor/market truncation or synthetic fill.
"""
from __future__ import annotations
import argparse
import collections
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

import compose_kinetic as composer
from check_kinetic import authenticate, imported


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def play(root, seed, seat, instrument=False):
    sys.path.insert(0, str(root))
    loader = imported('kinetic_game_loader', root/'checks/reference/evaluator/loader.py')
    # Parent verified all inputs before launching this isolated game process.
    engine, _ = loader.get_engine(root/'checks/reference/engine')
    main = imported('kinetic_native_entrypoint', root/'main.py')
    histogram = collections.Counter()
    if instrument:
        import mechanics
        original = mechanics._apply_unit_action
        def counted(*args, **kwargs):
            a = args[3]
            op = str(a[0]) if isinstance(a, list) and a else '<invalid>'
            histogram[op] += 1
            return original(*args, **kwargs)
        mechanics._apply_unit_action = counted
    cfg = loader.Struct({k: v.get('default') if isinstance(v, dict) else v
                         for k, v in engine.specification['configuration'].items()})
    cfg.seed = seed
    env = loader.Struct(configuration=cfg, done=False, info={})
    state = [loader.Struct(observation=loader.Struct(), action={}, status='ACTIVE', reward=0)
             for _ in range(2)]
    engine.interpreter(state, env)
    actions, states = hashlib.sha256(), hashlib.sha256()
    wall, cpu, statuses, daily = [], [], collections.Counter(), []
    for step in range(int(cfg.episodeSteps)):
        for s in state:
            s.observation.step = step
        observation = copy.deepcopy(state[seat].observation)
        started_wall, started_cpu = time.perf_counter(), time.process_time()
        action = main.agent(observation, cfg)
        cpu.append(time.process_time()-started_cpu)
        wall.append(time.perf_counter()-started_wall)
        instance = main._INSTANCE
        statuses['no-instance' if instance is None else instance.diagnostics.get('status', 'missing')] += 1
        state[seat].action = action
        state[1-seat].action = engine.starter_agent(copy.deepcopy(state[1-seat].observation))
        actions.update(encoded([s.action for s in state])+b'\n')
        engine.interpreter(state, env)
        states.update(encoded([dict(s) for s in state])+b'\n')
        if (step+1) % int(cfg.turnsPerDay) == 0 or all(s.status == 'DONE' for s in state):
            daily.append({'step': step, 'bank': [s.observation.farms[i]['money'] for i, s in enumerate(state)]})
        if all(s.status == 'DONE' for s in state):
            break
    return {'seed': seed, 'seat': seat, 'steps': step+1, 'scores': [s.reward for s in state],
            'terminal_status': [s.status for s in state], 'statuses': dict(statuses),
            'action_sha256': actions.hexdigest(), 'state_sha256': states.hexdigest(),
            'wall_seconds': sum(wall), 'cpu_seconds': sum(cpu), 'max_call_seconds': max(wall),
            'median_call_seconds': statistics.median(wall), 'per_call_wall_seconds': wall,
            'daily_bank': daily, 'instrumented': instrument, 'unit_histogram': dict(histogram)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seeds', default='17,101')
    parser.add_argument('--repetitions', type=int, default=2)
    parser.add_argument('--instrument', action='store_true')
    parser.add_argument('--order-offset', type=int, default=0)
    parser.add_argument('--child-seat', type=int, choices=[0, 1])
    parser.add_argument('--child-seed', type=int)
    parser.add_argument('--expected-mechanics-sha256')
    args = parser.parse_args()
    if args.child_seat is not None:
        if not args.expected_mechanics_sha256 or sha(args.native_root/'mechanics.py') != args.expected_mechanics_sha256:
            parser.error('Child mechanics identity mismatch')
        # Before loader import, verify every remaining manifest entry; no fetch fallback.
        manifest = json.loads((args.native_root/'SOURCE.json').read_text())
        for name, record in manifest['runtime'].items():
            expected = args.expected_mechanics_sha256 if name == 'mechanics.py' else record['sha256']
            if sha(args.native_root/name) != expected:
                parser.error(f'Child dependency changed: {name}')
        result = play(args.native_root, args.child_seed, args.child_seat, args.instrument)
        args.output.write_text(json.dumps(result, sort_keys=True, indent=2)+'\n')
        return 0
    if args.repetitions < 1:
        parser.error('At least one repetition is required')
    count = authenticate(args.native_root)
    seeds = [int(v) for v in args.seeds.split(',')]
    parent_source = (args.native_root/'mechanics.py').read_text()
    candidate_source = composer.compose(parent_source)
    results, pairs = [], []
    with tempfile.TemporaryDirectory(prefix='kinetic-native-') as scratch:
        scratch = Path(scratch)
        candidate = scratch/'candidate'
        shutil.copytree(args.native_root, candidate, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        (candidate/'mechanics.py').write_text(candidate_source)
        for name, record in json.loads((args.native_root/'SOURCE.json').read_text())['runtime'].items():
            if name != 'mechanics.py' and sha(candidate/name) != record['sha256']:
                raise ValueError(f'Unexpected candidate dependency change: {name}')
        for rep in range(args.repetitions):
            for seed in seeds:
                for seat in [0, 1]:
                    row_pair = {}
                    order = ['baseline', 'candidate'] if (rep+seat+args.order_offset) % 2 == 0 else ['candidate', 'baseline']
                    for arm in order:
                        root = args.native_root if arm == 'baseline' else candidate
                        result_file = scratch/'one-game.json'
                        command = [sys.executable] + (['-O'] if sys.flags.optimize else []) + [
                            str(Path(__file__).resolve()), '--native-root', str(root), '--output', str(result_file),
                            '--child-seat', str(seat), '--child-seed', str(seed),
                            '--expected-mechanics-sha256', sha(root/'mechanics.py')]
                        if args.instrument:
                            command.append('--instrument')
                        proc = subprocess.run(command, capture_output=True, text=True, timeout=90)
                        if proc.returncode:
                            raise RuntimeError(f'{arm} game failed: {proc.stdout}\n{proc.stderr}')
                        row = json.loads(result_file.read_text())
                        row.update(arm=arm, repetition=rep)
                        row_pair[arm] = row
                        results.append(row)
                        print(json.dumps({k: row[k] for k in ['arm', 'seed', 'seat', 'repetition', 'steps', 'scores',
                                                                  'statuses', 'wall_seconds', 'cpu_seconds']}, sort_keys=True), flush=True)
                    a, b = row_pair['baseline'], row_pair['candidate']
                    equal = all(a[k] == b[k] for k in ['action_sha256', 'state_sha256', 'scores', 'steps', 'terminal_status'])
                    complete = all(r['steps'] == 719 and r['terminal_status'] == ['DONE', 'DONE']
                                   and r['statuses'] == {'completed': 719} for r in [a, b])
                    pairs.append({'seed': seed, 'seat': seat, 'repetition': rep, 'parity': equal,
                                  'complete': complete, 'wall_ratio': b['wall_seconds']/a['wall_seconds'],
                                  'cpu_ratio': b['cpu_seconds']/a['cpu_seconds']})
    report = {'scope': 'b567 checked archive plus exactly one mechanics span; NOT current whole-V4 or field strength',
              'mode': 'optimized' if sys.flags.optimize else 'normal', 'instrumented': args.instrument,
              'order_offset': args.order_offset,
              'authenticated_runtime_members': count, 'source_manifest_sha256': sha(args.native_root/'SOURCE.json'),
              'source_mechanics_blob': composer.git_blob(parent_source.encode()),
              'candidate_mechanics_blob': composer.git_blob(candidate_source.encode()),
              'games': results, 'pairs': pairs,
              'summary': {'games': len(results), 'pairs': len(pairs),
                          'all_parity': all(p['parity'] for p in pairs),
                          'all_complete': all(p['complete'] for p in pairs),
                          'median_paired_wall_ratio': statistics.median(p['wall_ratio'] for p in pairs),
                          'median_paired_cpu_ratio': statistics.median(p['cpu_ratio'] for p in pairs)}}
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2)+'\n')
    print(json.dumps(report['summary'], sort_keys=True), flush=True)
    return 0 if report['summary']['all_parity'] and report['summary']['all_complete'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
