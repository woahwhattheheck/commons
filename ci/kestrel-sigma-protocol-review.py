#!/usr/bin/env python3
"""Focused full-package integration of Commons PR9326 and PR9327.

This is review-only wiring, not a replacement for the repository test battery.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys

BASE = '6ae371dc8207e9a2ad63d72c6036b07f18c16b94'
EXPECTED = {
    'protocol/events.py': 'c63bfbd2b97f7792c918f5ac2f1aac958dca6b5e',
    'protocol/schema.py': '0ed97c69d5ba2e13b639fe1c5de15718558cb3a2',
    'test_protocol_event_artifacts.py': '1fa64e20f680a8d19031089aaf79fb94716962e4',
    'test_protocol_timestamp_offsets.py': 'c4456557cae32edaffd755a7144e0949748aa0db',
}
OBSERVER = r'''
import json, pathlib, sys, unittest
suite = unittest.defaultTestLoader.loadTestsFromNames(sys.argv[2:])
result = unittest.TextTestRunner(verbosity=2).run(suite)
def problems(items):
    return [{'id': test.id(), 'trace': trace.replace(str(pathlib.Path.cwd()), '<repo>')} for test, trace in items]
report = {'tests_run': result.testsRun, 'failures': problems(result.failures),
          'errors': problems(result.errors),
          'skipped': [(test.id(), why) for test, why in result.skipped],
          'expected_failures': problems(result.expectedFailures),
          'unexpected_successes': [test.id() for test in result.unexpectedSuccesses],
          'success': result.wasSuccessful()}
pathlib.Path(sys.argv[1]).write_text(json.dumps(report, indent=2) + '\n')
sys.exit(0 if result.wasSuccessful() else 1)
'''


def run(command, cwd, logfile, timeout=180):
    print('$ ' + ' '.join(str(x) for x in command), flush=True)
    with logfile.open('wb') as stream:
        p = subprocess.Popen(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                             start_new_session=True)
        try:
            code = p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            raise RuntimeError(f'timed out: {command[0]}') from None
    print(f'exit={code} log={logfile.name}', flush=True)
    return code


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: protocol-review.py NEW_OUTPUT_DIRECTORY')
    root = Path(__file__).resolve().parents[1]
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=False)
    manifest = {'base': BASE, 'scope': 'focused full-package protocol review; not whole-repository CI',
                'source_blobs': {}, 'results': {}}
    try:
        for name, expected in EXPECTED.items():
            data = (root / name).read_bytes()
            sha = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            assert sha == expected, (name, sha, expected)
            manifest['source_blobs'][name] = sha
        manifest['review_sha'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
        assert run(['git', 'fetch', '--depth=1', 'https://github.com/woahwhattheheck/commons.git', BASE],
                   root, out / 'base-fetch.log', 180) == 0
        baseline = out / 'baseline'
        assert run(['git', 'worktree', 'add', '--detach', str(baseline), BASE], root, out / 'base-checkout.log') == 0
        for name in EXPECTED:
            if name.startswith('test_'):
                assert not (baseline / name).exists()
                shutil.copyfile(root / name, baseline / name)
        groups = {
            'new_protocol': ['test_protocol_event_artifacts', 'test_protocol_timestamp_offsets'],
            'observatory': ['test_protocol_observatory'],
            'keepalive_control': ['test_v1_grok_keepalive'],
        }
        for revision, cwd in [('base', baseline), ('combined', root)]:
            for group, modules in groups.items():
                key = revision + '-' + group
                result_path = out / (key + '.json')
                code = run([sys.executable, '-c', OBSERVER, str(result_path), *modules], cwd,
                           out / (key + '.log'), 180)
                assert result_path.exists(), (key, code)
                result = json.loads(result_path.read_text())
                assert code == (0 if result['success'] else 1), (key, code)
                manifest['results'][key] = result
                print(key, 'tests=', result['tests_run'], 'failures=', len(result['failures']),
                      'errors=', len(result['errors']), 'success=', result['success'], flush=True)
        results = manifest['results']
        assert results['combined-new_protocol']['tests_run'] == 22
        assert results['combined-new_protocol']['success']
        assert not results['combined-new_protocol']['skipped']
        assert results['base-new_protocol']['tests_run'] == 22
        assert not results['base-new_protocol']['success']
        for group in ('observatory', 'keepalive_control'):
            base, head = results['base-' + group], results['combined-' + group]
            assert base == head, (group, 'existing full-package outcomes changed')
        assert results['combined-observatory']['success'], 'existing Observatory regressions need examination'
        manifest['success'] = True
        print('PASS: 22 new full-package methods; existing Observatory passes; baseline control outcomes unchanged.', flush=True)
    except BaseException as exc:
        manifest['success'] = False
        manifest['failure'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        (out / 'summary.json').write_text(json.dumps(manifest, indent=2) + '\n')
        sums = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(out.glob('*')) if p.is_file()}
        (out / 'sha256.json').write_text(json.dumps(sums, indent=2) + '\n')


if __name__ == '__main__':
    main()
