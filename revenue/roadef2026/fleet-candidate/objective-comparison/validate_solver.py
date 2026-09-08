# SPDX-License-Identifier: MIT
"""Reproduce exact fleet solver parity and equal-work whole-process timings.

Inputs are a supplied original fleet main.cpp and its existing RapidJSON vendor
root. This creates four synthetic network instances, not a public/held challenge
screen. No network access, source overwrite, or submission operation is used.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import time

import integrate_compare


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def make_case(folder: Path, index: int, n: int, h: int, demand_count: int) -> list[Path]:
    folder.mkdir()
    rng = random.Random(27000 + index)
    node_ids = [10 * i + 3 for i in range(n)]
    pairs = {tuple(sorted((i, (i + 1) % n))) for i in range(n)}
    for _ in range(n * 3):
        pairs.add(tuple(sorted(rng.sample(range(n), 2))))
    links = []
    for a, b in sorted(pairs):
        metric, capacity = rng.randrange(1, 7), rng.randrange(20, 101)
        for u, v in ((a, b), (b, a)):
            links.append(dict(id=len(links), **{'from': node_ids[u]}, to=node_ids[v],
                              metric=metric, capacity=capacity))
    net = dict(directed=True, multigraph=False,
               nodes=[dict(id=i, name=str(i)) for i in node_ids], links=links)
    demands = []
    used_pairs = set()
    for _ in range(demand_count):
        a, b = rng.sample(node_ids, 2)
        while (a, b) in used_pairs:
            a, b = rng.sample(node_ids, 2)
        used_pairs.add((a, b))
        base = rng.randrange(5, 120)
        demands.append(dict(s=a, t=b, v=[rng.randrange(max(0, base-15), base+15) for _ in range(h)]))
    scenario = dict(max_segments=8, budget=[dict(t=t, value=rng.choice([0, 5, 20, 100]))
                                           for t in range(1, h)], interventions=[])
    paths = []
    for name, value in [('net', net), ('tm', dict(num_time_slots=h, demands=demands)),
                        ('scenario', scenario)]:
        path = folder / (name + '.json')
        # Unique demand endpoints also satisfy the official checker schema.
        path.write_text(json.dumps(value, sort_keys=True) + '\n', encoding='utf-8')
        paths.append(path)
    return paths


def run_solver(binary: Path, inputs: list[Path], folder: Path, tag: str,
               rounds: int, joint: int) -> tuple[dict, dict]:
    solution = folder / (tag + '.json')
    stat_path = folder / (tag + '-stats.json')
    # Remove inherited experiment controls; identical explicit controls for arms.
    env = {k: v for k, v in os.environ.items() if not k.startswith(('SEDGE_', 'FLEET_', 'CLOUD_'))}
    env.update(SEDGE_SECONDS='100000', SEDGE_MAX_ROUNDS=str(rounds),
               FLEET_JOINT=str(joint), FLEET_DIRECTED='1', FLEET_WAYPOINT_LIMIT='0',
               SEDGE_STATS=str(stat_path))
    start = time.perf_counter()
    done = subprocess.run([str(binary), *map(str, inputs), str(solution)], env=env,
                          capture_output=True, timeout=60)
    elapsed = time.perf_counter() - start
    (folder / (tag + '.stdout')).write_bytes(done.stdout)
    (folder / (tag + '.stderr')).write_bytes(done.stderr)
    done.check_returncode()
    stats = json.loads(stat_path.read_text(encoding='utf-8'))
    stats.pop('seconds')
    identity = dict(solution_sha256=sha(solution.read_bytes()), statistics=stats)
    return dict(wall_s=elapsed, **identity), identity


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--vendor', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--compiler', default='g++')
    p.add_argument('--samples', type=int, default=9)
    p.add_argument('--checker', type=Path, help='Existing pinned official checker; never downloaded here')
    args = p.parse_args()
    if args.samples < 1:
        p.error('samples must be positive')
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    original = args.source.read_bytes()
    changed = integrate_compare.apply(original.decode('utf-8')).encode('utf-8')
    if original == changed:
        raise ValueError('For a paired baseline use source without this shortcut')
    binaries = {}
    for tag, data in [('original', original), ('fast', changed)]:
        source = args.output / (tag + '.cpp')
        source.write_bytes(data)
        binary = args.output / tag
        cmd = [args.compiler, '-std=c++17', '-O3', '-DNDEBUG', '-I', str(args.vendor.resolve()),
               str(source), '-o', str(binary)]
        build = subprocess.run(cmd, capture_output=True, timeout=120)
        (args.output / (tag + '-build.log')).write_bytes(build.stdout + build.stderr)
        build.check_returncode()
        binaries[tag] = binary
    cases = []
    inputs_by_case = []
    for index, params in enumerate([(6,4,10), (12,12,30), (20,24,60), (30,40,80)]):
        folder = args.output / f'case-{index}'
        inputs = make_case(folder, index, *params)
        inputs_by_case.append(inputs)
        for joint in (0, 1):
            rows = {}; identity = None
            for tag in ('original', 'fast'):
                row, actual = run_solver(binaries[tag], inputs, folder, f'j{joint}-{tag}', 16, joint)
                rows[tag] = row
                if identity is None:
                    identity = actual
                elif identity != actual:
                    raise AssertionError(f'Work differs at case{index}/joint{joint}')
            cases.append(dict(case=index, dimensions=params, joint=joint, equal=True, arms=rows))
    checker_rows = []
    if args.checker is not None:
        for case in cases:
            index, joint = case['case'], case['joint']
            folder = args.output / f'case-{index}'
            inputs = inputs_by_case[index]
            # Both arms have byte-identical solutions: check one copy, retain
            # the equality binding instead of multiplying independent cases.
            solution = folder / f'j{joint}-fast.json'
            for decimals in (6, 12):
                cmd = [str(args.checker.resolve()), '--net', str(inputs[0]), '--tm', str(inputs[1]),
                       '--scenario', str(inputs[2]), '--srpaths', str(solution),
                       '--max-decimal-places', str(decimals)]
                done = subprocess.run(cmd, cwd=folder, capture_output=True, timeout=60)
                stem = f'j{joint}-checker-{decimals}'
                (folder / (stem + '.json')).write_bytes(done.stdout)
                (folder / (stem + '.stderr')).write_bytes(done.stderr)
                done.check_returncode()
                value = json.loads(done.stdout)
                if value.get('valid') is not True:
                    raise AssertionError('Official checker rejected paired solution')
                checker_rows.append(dict(case=index, joint=joint, decimals=decimals, valid=True,
                    report_sha256=sha(done.stdout), solution_sha256=sha(solution.read_bytes()),
                    checked_one_copy_of_identical_pair=True))
    samples = []; identity = None
    folder = args.output / 'case-3'
    for index in range(args.samples):
        row = dict(sample=index)
        for tag in (('original', 'fast') if index % 2 == 0 else ('fast', 'original')):
            result, actual = run_solver(binaries[tag], inputs_by_case[3], folder,
                                        f'time{index}-{tag}', 40, 1)
            row[tag] = result
            if identity is None:
                identity = actual
            elif identity != actual:
                raise AssertionError('Fixed-round work differs during timing')
        samples.append(row)
    medians = {tag: statistics.median(row[tag]['wall_s'] for row in samples)
               for tag in ('original', 'fast')}
    report = dict(schema='roadef.objective-compare.validation.v1',
                  source_sha256=sha(original), changed_sha256=sha(changed),
                  compiler=subprocess.check_output([args.compiler, '--version'], text=True).splitlines()[0],
                  platform=platform.platform(), cases=cases, checker_results=checker_rows, timing_samples=samples,
                  medians_s=medians, reduction_fraction=1-medians['fast']/medians['original'],
                  limits='Constructed networks and fixed work; not public benchmark scores or contest hardware. Checker execution is explicit above.')
    for name in ('cpu.max', 'memory.max'):
        path = Path('/sys/fs/cgroup') / name
        report[name] = path.read_text().strip() if path.exists() else None
    write_json(args.output / 'RESULTS.json', report)
    print(json.dumps(dict(parity_cases=len(cases), medians_s=medians,
                          reduction_fraction=report['reduction_fraction'])))


if __name__ == '__main__':
    main()
