"""Real executor checkpoint/CLI boundary with synthetic game rows, not game results.

The actual executor function bodies and standard-library imports are compiled
unchanged. Only unused top-level game/timing dependency initialization is omitted.
Filesystem replacement, serialization, fsync and the subprocess exit are real.
Set TITAN_EXECUTOR_PATH to exercise the exact pre-change executor.
"""
import ast
from contextlib import redirect_stdout
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

SOURCE = Path(os.environ.get('TITAN_EXECUTOR_PATH',
    Path(__file__).resolve().parents[1] / 'cloud-model-lab' / 'execute_arm.py'))


def read_executor():
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'), filename=str(SOURCE))
    tree.body = [node for node in tree.body if (
        isinstance(node, (ast.FunctionDef, ast.ImportFrom)) or
        isinstance(node, ast.Import) and not any(a.name == 'cards' for a in node.names))]
    namespace = {'__name__': '_checkpoint_contract', '__file__': str(SOURCE)}
    exec(compile(tree, str(SOURCE), 'exec'), namespace)
    return namespace


def game_row(seed=11, seat=0, opponent='arlene', arm='control', error=None):
    return {'seed': seed, 'seat': seat, 'opponent': opponent, 'arm': arm,
            'own_cash': None if error else 12.0,
            'rival_cash': None if error else 10.0,
            'margin': None if error else 2.0,
            'error': error, 'rounds': 719, 'worst_action_s': 0.012,
            'executor_timing': {'initialization_s': 0.01, 'first_action_s': 0.02},
            'path': [{'day': 0, 'draws': 0}]}


class CheckpointContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'out' / 'results.json'
        self.ns = read_executor()
        self.candidate = {'path': '/candidate.py', 'sha256': 'candidate-pin', 'label': 'candidate-pin'}
        self.control = {'path': '/control.py', 'sha256': 'control-pin', 'label': 'control-pin'}
        self.ns['load_callable'] = lambda path, extra: (
            object(), self.candidate if path == 'candidate.py' else self.control)

    def load(self):
        return json.loads(self.output.read_text(encoding='utf-8'))

    def invoke(self, game, seeds=('11',), with_path=False):
        self.ns['game'] = game
        argv = ['execute_arm.py', '--candidate', 'candidate.py', '--control', 'control.py',
                '--seeds', *seeds, '--seats', '0', '--opponents', 'arlene', '--out', str(self.output)]
        if not with_path:
            argv.append('--no-path')
        with patch.object(sys, 'argv', argv), redirect_stdout(io.StringIO()):
            self.ns['main']()

    def write(self, rows, expected=2, complete=False):
        self.ns['write_checkpoint'](str(self.output), self.candidate, self.control,
                                    rows, expected, complete)

    def test_control_is_saved_before_candidate_starts(self):
        def game(seed, seat, opponent, factory, label, record_path):
            if label == 'candidate':
                self.assertTrue(self.output.exists(), 'completed control must already be saved')
                saved = self.load()
                self.assertEqual([r['arm'] for r in saved['rows']], ['control'])
                self.assertEqual(saved['candidate'], self.candidate)
                self.assertEqual(saved['control'], self.control)
                self.assertFalse(saved['progress']['attempts_complete'])
            return game_row(seed, seat, opponent, label)
        self.invoke(game)

    def test_keyboard_interrupt_keeps_control(self):
        def game(seed, seat, opponent, factory, label, record_path):
            if label == 'candidate':
                raise KeyboardInterrupt('fixture interruption')
            return game_row(seed, seat, opponent, label)
        with self.assertRaises(KeyboardInterrupt):
            self.invoke(game)
        self.assertTrue(self.output.exists(), 'interrupt must retain returned control')
        self.assertEqual(len(self.load()['rows']), 1)
        self.assertFalse(self.load()['progress']['attempts_complete'])

    def test_later_interrupt_keeps_all_earlier_rows(self):
        def game(seed, seat, opponent, factory, label, record_path):
            if seed == 12 and label == 'candidate':
                raise SystemExit(7)
            return game_row(seed, seat, opponent, label)
        with self.assertRaises(SystemExit):
            self.invoke(game, ('11', '12'))
        self.assertTrue(self.output.exists(), 'three returned rows must survive')
        self.assertEqual([(r['seed'], r['arm']) for r in self.load()['rows']],
                         [(11, 'control'), (11, 'candidate'), (12, 'control')])
        self.assertEqual(self.load()['progress']['expected_games'], 4)

    def test_failed_row_is_saved_before_next_game(self):
        error = 'TypeError: original policy error'
        def game(seed, seat, opponent, factory, label, record_path):
            if label == 'candidate':
                self.assertTrue(self.output.exists(), 'failed attempt must be saved too')
                self.assertEqual(self.load()['rows'][0]['error'], error)
                self.assertIsNone(self.load()['rows'][0]['own_cash'])
            return game_row(seed, seat, opponent, label, error if label == 'control' else None)
        self.invoke(game)
        self.assertEqual(self.load()['progress']['failed_games'], 1)
        self.assertTrue(self.load()['progress']['attempts_complete'])

    def test_path_processing_failure_keeps_both_game_rows(self):
        module = types.ModuleType('market_path')
        def fail(*args):
            raise ValueError('path analysis failed')
        module.diff = fail
        with patch.dict(sys.modules, {'market_path': module}), self.assertRaisesRegex(ValueError, 'path analysis failed'):
            self.invoke(lambda s, p, o, f, a, r: game_row(s, p, o, a), with_path=True)
        self.assertTrue(self.output.exists(), 'both results precede path analysis')
        self.assertEqual(len(self.load()['rows']), 2)
        self.assertFalse(self.load()['progress']['attempts_complete'])

    def test_complete_panel_preserves_rows_order_metadata_and_timing(self):
        original = []
        def game(s, p, o, f, a, r):
            row = game_row(s, p, o, a)
            original.append(copy.deepcopy(row))
            return row
        self.invoke(game, ('11', '12'))
        saved = self.load()
        self.assertEqual(saved['rows'], original)
        self.assertEqual(saved['candidate'], self.candidate)
        self.assertEqual(saved['control'], self.control)
        self.assertEqual(saved['progress'], {'games_recorded': 4, 'expected_games': 4,
                                            'failed_games': 0, 'attempts_complete': True})

    def test_path_annotation_is_checkpointed(self):
        module = types.ModuleType('market_path')
        module.diff = lambda *args: ['one difference']
        with patch.dict(sys.modules, {'market_path': module}):
            self.invoke(lambda s, p, o, f, a, r: game_row(s, p, o, a), with_path=True)
        self.assertEqual(self.load()['rows'][1]['path_divergent_days'], 1)
        self.assertNotIn('path_divergent_days', self.load()['rows'][0])

    def test_partial_count_never_claims_all_attempts_returned(self):
        self.write([game_row()], expected=2, complete=True)
        self.assertFalse(self.load()['progress']['attempts_complete'])

    def test_replacement_error_preserves_previous_json_and_cleans_temp(self):
        self.write([game_row()])
        before = self.output.read_bytes()
        with patch.object(self.ns['os'], 'replace', side_effect=OSError('replace failed')):
            with self.assertRaisesRegex(OSError, 'replace failed'):
                self.write([game_row(), game_row(arm='candidate')])
        self.assertEqual(self.output.read_bytes(), before)
        self.assertEqual(list(self.output.parent.glob('*.tmp')), [])

    def test_serialization_error_preserves_previous_json(self):
        self.write([game_row()])
        before = self.output.read_bytes()
        row = game_row(); row['cycle'] = row
        with self.assertRaises(ValueError):
            self.write([row])
        self.assertEqual(self.output.read_bytes(), before)
        self.assertEqual(list(self.output.parent.glob('*.tmp')), [])

    def test_interrupted_write_preserves_previous_json(self):
        self.write([game_row()])
        before = self.output.read_bytes()
        with patch.object(self.ns['json'], 'dump', side_effect=KeyboardInterrupt('write interrupted')):
            with self.assertRaises(KeyboardInterrupt):
                self.write([game_row(arm='candidate')])
        self.assertEqual(self.output.read_bytes(), before)
        self.assertEqual(list(self.output.parent.glob('*.tmp')), [])

    def test_fsync_error_preserves_previous_json(self):
        self.write([game_row()])
        before = self.output.read_bytes()
        with patch.object(self.ns['os'], 'fsync', side_effect=OSError('sync failed')):
            with self.assertRaisesRegex(OSError, 'sync failed'):
                self.write([game_row(arm='candidate')])
        self.assertEqual(self.output.read_bytes(), before)
        self.assertEqual(list(self.output.parent.glob('*.tmp')), [])

    def test_replacement_is_same_directory_and_old_file_stays_whole_until_replace(self):
        self.write([game_row()])
        before = self.output.read_bytes()
        real_replace = os.replace
        def replace(src, dst):
            self.assertEqual(Path(src).parent, self.output.parent)
            self.assertEqual(self.output.read_bytes(), before)
            self.assertEqual(len(json.loads(Path(src).read_text())['rows']), 2)
            return real_replace(src, dst)
        with patch.object(self.ns['os'], 'replace', side_effect=replace):
            self.write([game_row(), game_row(arm='candidate')], complete=True)
        self.assertEqual(len(self.load()['rows']), 2)

    def test_relative_output_and_missing_directories(self):
        old = Path.cwd()
        try:
            os.chdir(self.root)
            self.ns['write_checkpoint']('relative.json', self.candidate, self.control, [], 0, True)
            self.assertTrue(json.loads(Path('relative.json').read_text())['progress']['attempts_complete'])
        finally:
            os.chdir(old)
        self.write([game_row()])
        self.assertTrue(self.output.exists())

    def test_real_process_exit_retains_completed_control(self):
        # Hard exit cannot run exception handlers or finalizers in the executor.
        script = '''
import importlib.util, os, sys
spec=importlib.util.spec_from_file_location("contract", sys.argv[1])
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
ns=mod.read_executor()
ns['load_callable']=lambda p, x: (object(), {'label':p,'path':p,'sha256':p})
def game(s,p,o,f,a,r):
    if a=='candidate': os._exit(23)
    return mod.game_row(s,p,o,a)
ns['game']=game
sys.argv=['execute_arm.py','--candidate','c.py','--control','b.py','--seeds','11',
          '--seats','0','--opponents','arlene','--no-path','--out',sys.argv[2]]
ns['main']()
'''
        result = subprocess.run([sys.executable, '-B', '-c', script, str(Path(__file__).resolve()), str(self.output)],
                                capture_output=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 23, result.stderr.decode(errors='replace'))
        self.assertTrue(self.output.exists(), 'hard process exit must retain returned control')
        self.assertEqual([r['arm'] for r in self.load()['rows']], ['control'])
        self.assertFalse(self.load()['progress']['attempts_complete'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
