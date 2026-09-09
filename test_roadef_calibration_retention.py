"""Calibration failure retention using synthetic files and real child processes."""
from __future__ import annotations
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

RUNNER = Path(__file__).resolve().parent / 'revenue/roadef2026/fleet-candidate/reference-calibration/run_calibration.py'

PORTFOLIO = '''import json, os, pathlib, sys
solution = pathlib.Path(sys.argv[4])
census = json.loads((solution.parent.parent / 'INPUTS.json').read_text())
assert len(census['input_files']) == 20
if os.environ['RETENTION_MODE'] == 'portfolio-fail':
    sys.exit(7)
solution.write_text('{}')
seconds = float(os.environ['PORTFOLIO_SECONDS'])
pathlib.Path(os.environ['PORTFOLIO_RECEIPT']).write_text(json.dumps({
    'deadline_seconds': seconds,
    'search_allowance_seconds': seconds - min(20.0, seconds * .12)}))
'''

CHECKER = '''import os, pathlib, sys
mode = os.environ['RETENTION_MODE']
first = pathlib.Path(sys.argv[sys.argv.index('--net')+1]).name.startswith('setA-01-')
if mode == 'utf8':
    sys.stdout.buffer.write(bytes([255]))
elif mode == 'malformed' or (mode == 'second-malformed' and not first):
    sys.stdout.write('{')
elif mode == 'invalid':
    sys.stdout.write('{"valid": false}')
else:
    sys.stdout.write('{"valid": true}')
if mode == 'checker-exit':
    sys.exit(3)
'''

@unittest.skipUnless(os.name == 'posix', 'Real executable fixtures require POSIX')
class CalibrationRetentionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='calibration-retention-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.frozen = self.root / 'frozen'
        self.context = self.root / 'context'
        self.official = self.root / 'official'
        self.output = self.root / 'output'
        self.frozen.mkdir()
        (self.context / 'bin').mkdir(parents=True)
        (self.official / 'setA').mkdir(parents=True)
        self.reference = self.root / 'reference.csv'
        self.reference.write_text('synthetic reference\n', encoding='utf-8')
        (self.frozen / 'main.cpp').write_text('// synthetic candidate\n', encoding='utf-8')
        (self.frozen / 'compare_checker.py').write_text(
            'def load_result(path): return {"vector": [1.0]}\n'
            'def load_sprint_reference(path): return {}\n', encoding='utf-8')
        for number in range(1, 21):
            for kind in ('net', 'tm', 'scenario'):
                (self.official / 'setA' / f'setA-{number:02d}-{kind}.json').write_text(
                    json.dumps({'case': number, 'kind': kind}), encoding='utf-8')
        for path, code in ((self.context/'run.sh', PORTFOLIO), (self.context/'bin/checker', CHECKER)):
            path.write_text('#!' + sys.executable + '\n' + code, encoding='utf-8')
            path.chmod(0o700)
        spec = importlib.util.spec_from_file_location('calibration_retention_under_test', RUNNER)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def exercise(self, mode):
        args = ['run_calibration.py', '--frozen-root', str(self.frozen),
                '--context', str(self.context), '--official-root', str(self.official),
                '--reference', str(self.reference), '--output', str(self.output),
                '--seconds', '2', '--case-timeout', '5']
        with mock.patch.object(sys, 'argv', args), mock.patch.dict(os.environ, {'RETENTION_MODE':mode}), \
             mock.patch.multiple(self.module,
                                 CANDIDATE_SHA256=self.module.sha256(self.frozen/'main.cpp'),
                                 SPRINT_SHA256=self.module.sha256(self.reference)), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'portfolio failed|official checker failed'):
                self.module.main()
        census = json.loads((self.output/'INPUTS.json').read_text())
        self.assertEqual(len(census['input_files']), 20)
        for row in census['input_files']:
            for name, kind in (('network','net'), ('traffic','tm'), ('scenario','scenario')):
                raw = (self.official/'setA'/f'{row["instance"]}-{kind}.json').read_bytes()
                self.assertEqual(row[name], {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
        self.assertFalse((self.output/'RUN.json').exists())
        return json.loads((self.output/'RUN-PARTIAL.json').read_text())['runs']

    def assert_checker_failure(self, rows, error, code=0):
        row = rows[-1]
        self.assertEqual(row['portfolio_returncode'], 0)
        self.assertEqual(row['checker_returncode'], code)
        self.assertEqual(row['checker_parse_error'], error)
        for name, filename in (('solution','solution.json'), ('receipt','portfolio.json'), ('checker','checker-6.json')):
            self.assertTrue(row[name+'_exists'])
            raw = (self.output/row['instance']/filename).read_bytes()
            self.assertEqual(row[name+'_sha256'], hashlib.sha256(raw).hexdigest())

    def test_census_survives_first_portfolio_failure(self):
        rows = self.exercise('portfolio-fail')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['returncode'], 7)
        self.assertFalse(rows[0]['solution_exists'])

    def test_malformed_json_retains_current_case(self):
        rows = self.exercise('malformed')
        self.assertEqual(len(rows), 1)
        self.assert_checker_failure(rows, 'JSONDecodeError')

    def test_invalid_utf8_retains_current_case(self):
        self.assert_checker_failure(self.exercise('utf8'), 'UnicodeDecodeError')

    def test_invalid_result_remains_a_failure(self):
        rows = self.exercise('invalid')
        self.assert_checker_failure(rows, None)
        self.assertFalse(rows[-1]['checker_valid'])

    def test_nonzero_checker_exit_remains_a_failure(self):
        rows = self.exercise('checker-exit')
        self.assert_checker_failure(rows, None, code=3)
        self.assertTrue(rows[-1]['checker_valid'])

    def test_earlier_success_is_preserved_before_later_parse_failure(self):
        rows = self.exercise('second-malformed')
        self.assertEqual([r['instance'] for r in rows], ['setA-01','setA-02'])
        self.assertEqual(rows[0]['checker_returncode'], 0)
        self.assertEqual(rows[0]['load_count'], 1)
        self.assert_checker_failure(rows, 'JSONDecodeError')

if __name__ == '__main__':
    unittest.main(verbosity=2)
