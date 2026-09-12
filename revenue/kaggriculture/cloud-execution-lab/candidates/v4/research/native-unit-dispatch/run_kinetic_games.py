# SPDX-License-Identifier: Apache-2.0
"""Offline native-entrypoint parity and alternating timing, one game per process.

Authenticates the complete checked native package from bytes captured exactly once
before cloning. Child game processes execute the already-authenticated captured
runner bytes through a tiny parent-owned stdin bootstrap; they never reopen a
repository or scratch runner pathname. No repository control helper is imported
before capture/authentication; the composer is compiled and executed only from
already-authenticated captured bytes. Runner provenance is supplied from external
exact-head authority rather than inferred from the mutable checkout. Changes only
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
from pathlib import Path, PurePosixPath
import statistics
import subprocess
import sys
import tempfile
import time
import types

SOURCE_SHA256 = 'e87d70dd3bcf5aea1e929f1a5dbdc86f3cc33d8a0b3492986f2970fc8e774be2'
BASE_MECHANICS_BLOB = '044a4f9c0a4a44dde10ada57563238bcaf82075d'
ENGINE_GIT_BLOBS = {
    'checks/reference/engine/kaggriculture.py': '3c202c7ee921da239356789e266b694635103fc4',
    'checks/reference/engine/kaggriculture.json': 'b354d06b742fe48402513792253f1a5c29366b20',
    'checks/reference/engine/utils.py': '91c8822ee6201ba4a5a8416c7dbe34f95dd61c87',
}
CONTROL_FILES = ('run_kinetic_games.py', 'compose_kinetic.py', 'check_kinetic.py')
CONTROL_GIT_BLOBS = {
    'compose_kinetic.py': 'd34362e98277c930b7b28519f2892bea758b3878',
    'check_kinetic.py': 'a8bf67cca8f34492dc28286da62168da5d59c146',
}
CAPTURED_RUNNER_BOOTSTRAP = r'''import hashlib
import sys
expected = sys.argv.pop(1)
raw = sys.stdin.buffer.read()
actual = hashlib.sha1(b"blob " + str(len(raw)).encode() + bytes([0]) + raw).hexdigest()
if actual != expected:
    raise SystemExit("captured runner Git blob mismatch before exec")
namespace = {
    "__name__": "__main__",
    "__file__": "<captured-run_kinetic_games.py>",
    "__package__": None,
    "_KINETIC_BOOTSTRAP_RUNNER_BLOB": actual,
}
exec(compile(raw, namespace["__file__"], "exec"), namespace, namespace)
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw):
    """Git blob identity owned by this runner, not by a repo-path helper."""
    if not isinstance(raw, bytes):
        raise TypeError('git_blob requires bytes')
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def _git_blob_pin(value, name='expected runner Git blob'):
    if not isinstance(value, str) or len(value) != 40 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError(f'Invalid {name}')
    return value


def _sha256_pin(value, name='expected SHA-256'):
    if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError(f'Invalid {name}')
    return value


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def imported(name, path):
    """Load a module from an already-custodied path without checker dependency."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f'Cannot load module: {path}')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def _safe_relative(name):
    if not isinstance(name, str) or not name or '\\' in name:
        raise ValueError(f'Unsafe runtime member: {name!r}')
    rel = PurePosixPath(name)
    if rel.is_absolute() or '..' in rel.parts or '.' in rel.parts:
        raise ValueError(f'Unsafe runtime member: {name!r}')
    return Path(*rel.parts)


def control_bundle_digest(captured):
    """Length-delimited digest of the exact parent-authenticated control bytes."""
    if set(captured) != set(CONTROL_FILES):
        raise ValueError('Incomplete control bundle')
    digest = hashlib.sha256()
    for name in CONTROL_FILES:
        raw = captured[name]
        if not isinstance(raw, bytes):
            raise ValueError(f'Invalid control bytes: {name}')
        encoded_name = name.encode('utf-8')
        digest.update(len(encoded_name).to_bytes(4, 'big'))
        digest.update(encoded_name)
        digest.update(len(raw).to_bytes(8, 'big'))
        digest.update(raw)
    return digest.hexdigest()


def capture_control_bundle(root, expected_runner_git_blob):
    """Capture runner plus pinned helpers exactly once under external runner identity.

    ``expected_runner_git_blob`` MUST come from external exact-head authority
    (GitHub/executor/workflow), never by re-reading the mutable checkout being
    authenticated. No helper from this bundle is imported or executed before this
    routine. Helper pins are verified with runner-owned ``git_blob`` code.
    """
    expected_runner_git_blob = _git_blob_pin(expected_runner_git_blob)
    root = Path(root).resolve(strict=True)
    captured = {}
    for name in CONTROL_FILES:
        path = root / name
        if path.is_symlink() or not path.is_file() or path.resolve(strict=True).parent != root:
            raise ValueError(f'Unsafe control input: {name}')
        raw = path.read_bytes()
        actual_blob = git_blob(raw)
        if name == 'run_kinetic_games.py':
            if actual_blob != expected_runner_git_blob:
                raise ValueError('Unverified control runner')
        else:
            expected_blob = CONTROL_GIT_BLOBS[name]
            if actual_blob != expected_blob:
                raise ValueError(f'Unverified control input: {name}')
        captured[name] = raw
    return captured, control_bundle_digest(captured)


def load_captured_composer(raw):
    """Execute only the already-authenticated composer capture privately."""
    if git_blob(raw) != CONTROL_GIT_BLOBS['compose_kinetic.py']:
        raise ValueError('Unverified captured composer')
    try:
        source = raw.decode('utf-8')
    except UnicodeError as exc:
        raise ValueError('Captured composer is not UTF-8') from exc
    module = types.ModuleType('kinetic_captured_composer')
    module.__file__ = '<captured-compose_kinetic.py>'
    exec(compile(source, module.__file__, 'exec'), module.__dict__)
    if getattr(module, 'BASE_BLOB', None) != BASE_MECHANICS_BLOB:
        raise ValueError('Captured composer baseline identity mismatch')
    if not callable(getattr(module, 'compose', None)):
        raise ValueError('Captured composer missing compose()')
    return module


def run_captured_runner(runner_bytes, expected_runner_git_blob, runner_args, *, python_flags=(), timeout=90):
    """Start a fresh Python process from authenticated runner bytes, never a path.

    The parent rechecks the captured bytes, supplies them on stdin, and executes a
    constant bootstrap with ``python -c``. The bootstrap hashes stdin against the
    externally sourced runner Git blob before compiling/executing it and injects
    the attested identity into the runner globals. No materialized runner pathname
    exists for an attacker to swap between parent validation and child launch.
    """
    expected_runner_git_blob = _git_blob_pin(expected_runner_git_blob)
    if not isinstance(runner_bytes, bytes):
        raise TypeError('runner_bytes must be bytes')
    if git_blob(runner_bytes) != expected_runner_git_blob:
        raise ValueError('Captured runner bytes do not match external identity')
    if not isinstance(runner_args, (list, tuple)) or any(not isinstance(v, str) for v in runner_args):
        raise ValueError('runner_args must be strings')
    if not isinstance(python_flags, (list, tuple)) or any(not isinstance(v, str) for v in python_flags):
        raise ValueError('python_flags must be strings')
    command = [
        sys.executable,
        *python_flags,
        '-c',
        CAPTURED_RUNNER_BOOTSTRAP,
        expected_runner_git_blob,
        *runner_args,
    ]
    return subprocess.run(
        command,
        input=runner_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def capture_runtime(root, expected_mechanics_sha256=None):
    """Capture and authenticate every declared runtime byte exactly once.

    The returned byte buffers are the sole source for later materialization and
    execution. ``expected_mechanics_sha256`` is permitted only for the composed
    candidate; every other runtime member remains bound to SOURCE.json.
    """
    root = Path(root).resolve(strict=True)
    manifest_raw = (root / 'SOURCE.json').read_bytes()
    if sha_bytes(manifest_raw) != SOURCE_SHA256:
        raise ValueError('Unverified SOURCE manifest')
    manifest = json.loads(manifest_raw)
    runtime_manifest = manifest.get('runtime')
    if not isinstance(runtime_manifest, dict) or not runtime_manifest:
        raise ValueError('Invalid SOURCE runtime manifest')
    captured = {}
    for name, pin in runtime_manifest.items():
        rel = _safe_relative(name)
        if not isinstance(pin, dict) or not isinstance(pin.get('sha256'), str):
            raise ValueError(f'Invalid runtime pin: {name}')
        path = root / rel
        if path.is_symlink() or not path.is_file() or not path.resolve(strict=True).is_relative_to(root):
            raise ValueError(f'Unsafe runtime input: {name}')
        raw = path.read_bytes()
        expected = expected_mechanics_sha256 if name == 'mechanics.py' and expected_mechanics_sha256 else pin['sha256']
        if sha_bytes(raw) != expected:
            raise ValueError(f'Unverified runtime input: {name}')
        captured[name] = raw
    if 'mechanics.py' not in captured:
        raise ValueError('SOURCE runtime is missing mechanics.py')
    if expected_mechanics_sha256 is None and git_blob(captured['mechanics.py']) != BASE_MECHANICS_BLOB:
        raise ValueError('Expected immutable original mechanics input')
    for name, expected_blob in ENGINE_GIT_BLOBS.items():
        if name not in captured or git_blob(captured[name]) != expected_blob:
            raise ValueError(f'Unverified engine input: {name}')
    return manifest_raw, captured


def materialize_runtime(root, manifest_raw, captured):
    """Write an authenticated runtime capture into a fresh execution tree."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    (root / 'SOURCE.json').write_bytes(manifest_raw)
    for name, raw in captured.items():
        path = root / _safe_relative(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)


def play(root, seed, seat, instrument=False):
    sys.path.insert(0, str(root))
    loader = imported('kinetic_game_loader', root/'checks/reference/evaluator/loader.py')
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


def _require_captured_child_identity(expected_runner_git_blob):
    actual = globals().get('_KINETIC_BOOTSTRAP_RUNNER_BLOB')
    if actual != expected_runner_git_blob:
        raise ValueError('Child runner was not launched from authenticated captured bytes')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-runner-git-blob', required=True,
                        help='external exact-head Git blob for run_kinetic_games.py')
    parser.add_argument('--seeds', default='17,101')
    parser.add_argument('--repetitions', type=int, default=2)
    parser.add_argument('--instrument', action='store_true')
    parser.add_argument('--order-offset', type=int, default=0)
    parser.add_argument('--child-seat', type=int, choices=[0, 1])
    parser.add_argument('--child-seed', type=int)
    parser.add_argument('--expected-mechanics-sha256')
    parser.add_argument('--expected-control-bundle-sha256')
    parser.add_argument('--control-probe', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    expected_runner_git_blob = _git_blob_pin(args.expected_runner_git_blob)

    if args.control_probe:
        _require_captured_child_identity(expected_runner_git_blob)
        if not args.expected_control_bundle_sha256:
            parser.error('Control bundle identity is required')
        control_digest = _sha256_pin(
            args.expected_control_bundle_sha256, 'expected control bundle SHA-256'
        )
        args.output.write_text(json.dumps({
            'executed_control_bundle_sha256': control_digest,
            'executed_control_runner_blob': expected_runner_git_blob,
            'executed_control_compose_blob': CONTROL_GIT_BLOBS['compose_kinetic.py'],
            'executed_control_check_blob': CONTROL_GIT_BLOBS['check_kinetic.py'],
            'runner_executed_from_captured_bytes': True,
        }, sort_keys=True, indent=2)+'\n')
        return 0

    if args.child_seat is not None:
        _require_captured_child_identity(expected_runner_git_blob)
        if not args.expected_mechanics_sha256:
            parser.error('Child mechanics identity is required')
        if not args.expected_control_bundle_sha256:
            parser.error('Child control bundle identity is required')
        control_digest = _sha256_pin(
            args.expected_control_bundle_sha256, 'expected control bundle SHA-256'
        )
        manifest_raw, captured = capture_runtime(args.native_root, args.expected_mechanics_sha256)
        with tempfile.TemporaryDirectory(prefix='kinetic-child-snapshot-') as tmp:
            frozen = Path(tmp) / 'runtime'
            materialize_runtime(frozen, manifest_raw, captured)
            result = play(frozen, args.child_seed, args.child_seat, args.instrument)
        result['executed_source_manifest_sha256'] = sha_bytes(manifest_raw)
        result['executed_mechanics_sha256'] = sha_bytes(captured['mechanics.py'])
        result['executed_control_bundle_sha256'] = control_digest
        result['executed_control_runner_blob'] = expected_runner_git_blob
        result['executed_control_compose_blob'] = CONTROL_GIT_BLOBS['compose_kinetic.py']
        result['executed_control_check_blob'] = CONTROL_GIT_BLOBS['check_kinetic.py']
        result['runner_executed_from_captured_bytes'] = True
        args.output.write_text(json.dumps(result, sort_keys=True, indent=2)+'\n')
        return 0
    if args.repetitions < 1:
        parser.error('At least one repetition is required')

    control_files, control_digest = capture_control_bundle(
        Path(__file__).resolve().parent, expected_runner_git_blob
    )
    composer = load_captured_composer(control_files['compose_kinetic.py'])
    control_runner_bytes = control_files['run_kinetic_games.py']
    control_runner_blob = git_blob(control_runner_bytes)
    if control_runner_blob != expected_runner_git_blob:
        raise ValueError('Parent control runner identity mismatch')
    manifest_raw, baseline_files = capture_runtime(args.native_root)
    count = len(baseline_files)
    seeds = [int(v) for v in args.seeds.split(',')]
    parent_bytes = baseline_files['mechanics.py']
    parent_source = parent_bytes.decode()
    candidate_source = composer.compose(parent_source)
    candidate_bytes = candidate_source.encode()
    baseline_mechanics_sha256 = sha_bytes(parent_bytes)
    candidate_mechanics_sha256 = sha_bytes(candidate_bytes)
    results, pairs = [], []
    with tempfile.TemporaryDirectory(prefix='kinetic-native-') as scratch:
        scratch = Path(scratch)
        baseline = scratch/'baseline'
        candidate = scratch/'candidate'
        materialize_runtime(baseline, manifest_raw, baseline_files)
        candidate_files = dict(baseline_files)
        candidate_files['mechanics.py'] = candidate_bytes
        materialize_runtime(candidate, manifest_raw, candidate_files)
        for rep in range(args.repetitions):
            for seed in seeds:
                for seat in [0, 1]:
                    row_pair = {}
                    order = ['baseline', 'candidate'] if (rep+seat+args.order_offset) % 2 == 0 else ['candidate', 'baseline']
                    for arm in order:
                        root = baseline if arm == 'baseline' else candidate
                        expected_mechanics = baseline_mechanics_sha256 if arm == 'baseline' else candidate_mechanics_sha256
                        result_file = scratch/'one-game.json'
                        python_flags = ['-B']
                        if sys.flags.optimize:
                            python_flags.insert(0, '-O')
                        runner_args = [
                            '--native-root', str(root), '--output', str(result_file),
                            '--expected-runner-git-blob', expected_runner_git_blob,
                            '--child-seat', str(seat), '--child-seed', str(seed),
                            '--expected-mechanics-sha256', expected_mechanics,
                            '--expected-control-bundle-sha256', control_digest,
                        ]
                        if args.instrument:
                            runner_args.append('--instrument')
                        proc = run_captured_runner(
                            control_runner_bytes,
                            expected_runner_git_blob,
                            runner_args,
                            python_flags=python_flags,
                            timeout=90,
                        )
                        if proc.returncode:
                            stdout = proc.stdout.decode('utf-8', errors='replace')
                            stderr = proc.stderr.decode('utf-8', errors='replace')
                            raise RuntimeError(f'{arm} game failed: {stdout}\n{stderr}')
                        row = json.loads(result_file.read_text())
                        if row.get('executed_mechanics_sha256') != expected_mechanics:
                            raise ValueError(f'{arm} child executed unexpected mechanics bytes')
                        if row.get('executed_source_manifest_sha256') != sha_bytes(manifest_raw):
                            raise ValueError(f'{arm} child executed under unexpected source manifest')
                        if row.get('executed_control_bundle_sha256') != control_digest:
                            raise ValueError(f'{arm} child executed unexpected control bundle')
                        if row.get('executed_control_runner_blob') != expected_runner_git_blob:
                            raise ValueError(f'{arm} child executed unexpected runner bytes')
                        if row.get('runner_executed_from_captured_bytes') is not True:
                            raise ValueError(f'{arm} child lacks captured-runner execution receipt')
                        if row.get('executed_control_compose_blob') != CONTROL_GIT_BLOBS['compose_kinetic.py']:
                            raise ValueError(f'{arm} child executed unexpected composer bytes')
                        if row.get('executed_control_check_blob') != CONTROL_GIT_BLOBS['check_kinetic.py']:
                            raise ValueError(f'{arm} child executed unexpected checker bytes')
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
              'order_offset': args.order_offset, 'authenticated_runtime_members': count,
              'source_manifest_sha256': sha_bytes(manifest_raw),
              'source_mechanics_blob': git_blob(parent_bytes),
              'candidate_mechanics_blob': git_blob(candidate_bytes),
              'source_mechanics_sha256': baseline_mechanics_sha256,
              'candidate_mechanics_sha256': candidate_mechanics_sha256,
              'control_bundle_sha256': control_digest,
              'control_runner_git_blob': control_runner_blob,
              'control_runner_external_pin': expected_runner_git_blob,
              'control_compose_git_blob': CONTROL_GIT_BLOBS['compose_kinetic.py'],
              'control_check_git_blob': CONTROL_GIT_BLOBS['check_kinetic.py'],
              'immutable_execution_snapshot': True,
              'immutable_control_snapshot': True,
              'child_runner_execution': 'captured_bytes_stdin_bootstrap',
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
