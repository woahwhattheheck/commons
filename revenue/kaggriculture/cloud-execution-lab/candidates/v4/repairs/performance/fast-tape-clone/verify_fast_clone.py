# SPDX-License-Identifier: Apache-2.0
"""Run recovered clone proofs in scratch; never run a legacy materializer.

Default: original 20 helper tests plus 8 independent graph tests, using
main's pinned donor tape. --generated-only explicitly runs only the 8
fixture-free tests. --legacy-port adds 11 historical AST/seam tests and
requires exact parent-generator and archived-router inputs; it does not
certify current-production ABI compatibility.
"""
import argparse
import ast
import base64
import hashlib
import json
import lzma
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
HELPER = 'r04_fast_tape_clone.py'
GRAPH_TEST = 'test_fast_clone_graph_contract.py'
ORIGINAL_TEST = 'test_r04_fast_tape_clone.py'
PINS = {
    HELPER: 'b7c1fd2f7f786c5dc5f8a3b9a7116815ea40607a',
    GRAPH_TEST: 'da78c6664ff9b0537a910cf4672355fcaafb0a9e',
    ORIGINAL_TEST: 'a292131f3a9b47c00d74585ca2691beb07fbb44a',
    'r01_tapes.py': 'a43289b9cc5e34a2481fddf652762a7d92f427ef',
    'port_fast_tape_clone.py': '39bb7f9bf95cfa32a99c1a30843ba47d506709ad',
    'test_port_fast_tape_clone.py': 'bc9360e0c854b7073755cf24c737b81c74eb8dbf',
    'parent_apply_v4.py': 'fb766feaba84f10edbc1766f7c3404e6e00347a5',
    'r04_full_router.py': '21c4f1db0298f8955b1f5ad366bd780a89cad206',
}
DRIVER = '''import json, sys, unittest
suite = unittest.defaultTestLoader.discover(sys.argv[1], pattern="test*.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
valid = result.wasSuccessful() and not result.skipped and result.testsRun == int(sys.argv[2])
print(json.dumps({"tests": result.testsRun, "skipped": len(result.skipped), "ok": valid}))
raise SystemExit(0 if valid else 1)
'''


def git_blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def read_pinned(path, name):
    data = Path(path).read_bytes()
    actual = git_blob(data)
    if actual != PINS[name]:
        raise ValueError(f'{name}: expected {PINS[name]}, found {actual} at {path}')
    return data


def tape_json(data):
    # AST-only reading of the immutable corpus; no import of donor tape code.
    nodes = [n for n in ast.parse(data).body if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == '_B85' for t in n.targets)]
    if len(nodes) != 1:
        raise ValueError('expected exactly one tape _B85 assignment')
    encoded = ast.literal_eval(nodes[0].value)
    tapes = json.loads(lzma.decompress(base64.b85decode(encoded)))
    if not isinstance(tapes, list) or len(tapes) != 13:
        raise ValueError('expected 13 tapes')
    if any(not isinstance(t, list) or len(t) != 719 for t in tapes):
        raise ValueError('expected 719 actions per tape')
    return json.dumps(tapes, separators=(',', ':')).encode()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated-only', action='store_true')
    parser.add_argument('--tapes', type=Path)
    parser.add_argument('--legacy-port', action='store_true')
    parser.add_argument('--parent-apply', type=Path)
    parser.add_argument('--archived-router', type=Path)
    args = parser.parse_args(argv)
    if args.generated_only and args.legacy_port:
        parser.error('--generated-only cannot include --legacy-port')
    if args.legacy_port and (args.parent_apply is None or args.archived_router is None):
        parser.error('--legacy-port requires --parent-apply and --archived-router')
    if not args.legacy_port and (args.parent_apply is not None or args.archived_router is not None):
        parser.error('historical inputs require explicit --legacy-port')
    if args.generated_only and args.tapes is not None:
        parser.error('--generated-only does not consume --tapes')
    try:
        inputs = {HELPER: read_pinned(HERE / HELPER, HELPER),
                  GRAPH_TEST: read_pinned(HERE / GRAPH_TEST, GRAPH_TEST)}
        expected = 8
        if not args.generated_only:
            path = args.tapes
            if path is None:
                path = HERE.parents[2] / 'donor' / 'overlay' / 'r01_tapes.py'
            inputs[ORIGINAL_TEST] = read_pinned(HERE / ORIGINAL_TEST, ORIGINAL_TEST)
            inputs['r01_tapes.py'] = read_pinned(path, 'r01_tapes.py')
            # Validate shape even when only the original helper suite consumes it.
            decoded = tape_json(inputs['r01_tapes.py'])
            expected += 20
        if args.legacy_port:
            for name in ('port_fast_tape_clone.py', 'test_port_fast_tape_clone.py'):
                inputs[name] = read_pinned(HERE / name, name)
            inputs['parent_apply_v4.py'] = read_pinned(args.parent_apply, 'parent_apply_v4.py')
            inputs['predecessor-package/r04_full_router.py'] = read_pinned(
                args.archived_router, 'r04_full_router.py')
            inputs['tapes.json'] = decoded
            expected += 11
        hashes = {name: git_blob(data) for name, data in inputs.items()}
        results = []
        with tempfile.TemporaryDirectory(prefix='titan-v4-clone-') as temporary:
            stage = Path(temporary)
            for name, data in inputs.items():
                path = stage / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                if path.read_bytes() != data:
                    raise ValueError('scratch readback mismatch: ' + name)
            (stage / 'run_suite.py').write_text(DRIVER, encoding='utf-8')
            for optimized in (False, True):
                command = [sys.executable, '-I'] + (['-O'] if optimized else [])
                command += [str(stage / 'run_suite.py'), str(stage), str(expected)]
                done = subprocess.run(command, cwd=stage, capture_output=True, text=True, timeout=120)
                sys.stderr.write(done.stderr)
                if done.returncode:
                    sys.stderr.write(done.stdout)
                    return 1
                summary = json.loads(done.stdout)
                if summary != {'tests': expected, 'skipped': 0, 'ok': True}:
                    raise ValueError('unexpected test result: ' + repr(summary))
                results.append({'optimized': optimized, **summary})
        print(json.dumps({'status': 'PASS', 'scope': 'historical-clone-source-only',
                          'generated_only': args.generated_only, 'legacy_port': args.legacy_port,
                          'input_blobs': hashes, 'runs': results,
                          'production_changed': False}, sort_keys=True))
        return 0
    except (OSError, ValueError, SyntaxError, EOFError, lzma.LZMAError,
            subprocess.TimeoutExpired) as exc:
        print(f'fast-clone verification failed: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
