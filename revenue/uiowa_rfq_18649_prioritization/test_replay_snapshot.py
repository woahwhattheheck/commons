"""Replay lifetime regressions with disposable sources and benign file edits.

The reference double below only removes the current run's additional manifest,
so it can exercise the replay's seven-file lifetime contract without requiring
Git history. It is NOT evidence of equivalence with the retained old calculator.
That separate check uses the actual pinned baseline via replay_integrity.py.
"""
from __future__ import annotations

import builtins
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest import mock

HERE = Path(__file__).resolve().parent
REFERENCE_SUFFIX = b'''
# Test-only reference double: all writes are inside disposable test output.
_reference_with_manifest = run
def run(input_csv, weights_path, out_dir):
    result = _reference_with_manifest(input_csv, weights_path, out_dir)
    (out_dir / "manifest.json").unlink()
    return result
'''


def load_bytes(name, path, data):
    module = ModuleType(name)
    module.__file__ = str(path)
    exec(compile(data, str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


class ReplaySnapshotTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = (HERE / 'prioritize.py').read_bytes()
        for name in ('prioritize.py', 'recommendations.synthetic.csv', 'weights.json'):
            (self.root / name).write_bytes((HERE / name).read_bytes())
        calculator = load_bytes('prioritize', self.root / 'prioritize.py', self.source)
        # Give the predecessor its real import behavior. The correction must not
        # reuse this already-imported module when it captures a new source.
        with mock.patch.dict(sys.modules, {'prioritize': calculator}):
            self.replay = load_bytes('replay_subject', self.root / 'replay_integrity.py',
                                     (HERE / 'replay_integrity.py').read_bytes())
        self.reference = self.source + REFERENCE_SUFFIX
        self.baseline = self.root / 'baseline.py'
        self.baseline.write_bytes(self.reference)
        self.replay.BASELINE_BLOB = self.replay.git_blob(self.reference)
        self.before = self.input_bytes()

    def input_bytes(self):
        return {name: (self.root / name).read_bytes() for name in
                ('prioritize.py', 'baseline.py', 'recommendations.synthetic.csv', 'weights.json')}

    def run_replay(self, name='out'):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.replay.replay(self.baseline, self.root / name)

    def test_fixture_edit_after_pin_does_not_change_used_fixture(self):
        clean = self.run_replay('clean')
        target = self.root / 'recommendations.synthetic.csv'
        read = Path.read_bytes
        seen = 0
        def observed(path):
            nonlocal seen
            data = read(path)
            if path == target:
                seen += 1
                if seen == 1:
                    path.write_bytes(data.replace(b'Automate deployment provenance',
                                                  b'Editorially revised title'))
            return data
        with mock.patch.object(Path, 'read_bytes', observed):
            changed = self.run_replay('changed')
        self.assertEqual(changed['unchanged_output_files'], clean['unchanged_output_files'])
        self.assertEqual(changed['change'], clean['change'])

    def test_source_edit_after_fixture_pin_cannot_relabel_executed_source(self):
        target = self.root / 'recommendations.synthetic.csv'
        read = Path.read_bytes
        changed = False
        def observed(path):
            nonlocal changed
            data = read(path)
            if path == target and not changed:
                changed = True
                (self.root / 'prioritize.py').write_bytes(self.source + b'\n# editorial update\n')
            return data
        with mock.patch.object(Path, 'read_bytes', observed):
            result = self.run_replay()
        self.assertTrue(changed)
        self.assertEqual(result['tested_source_blob'], self.replay.git_blob(self.source))

    def test_baseline_compile_uses_pinned_buffer_not_later_path(self):
        read, compile_source = Path.read_bytes, builtins.compile
        captured = []
        def observed_read(path):
            data = read(path)
            if path == self.baseline:
                path.write_bytes(data + b'\n# editorial baseline update\n')
            return data
        def observed_compile(source, *args, **kwargs):
            if isinstance(source, bytes) and b'_reference_with_manifest' in source:
                captured.append(source)
            return compile_source(source, *args, **kwargs)
        with mock.patch.object(Path, 'read_bytes', observed_read), \
                mock.patch.object(builtins, 'compile', observed_compile):
            self.run_replay()
        self.assertEqual(captured, [self.reference])

    def test_each_source_and_fixture_path_is_read_once(self):
        paths = {self.root / name: 0 for name in self.before}
        read = Path.read_bytes
        def observed(path):
            if path in paths:
                paths[path] += 1
            return read(path)
        with mock.patch.object(Path, 'read_bytes', observed):
            self.run_replay()
        self.assertEqual(paths, {path: 1 for path in paths})

    def test_receipt_binds_exact_fixture_bytes(self):
        result = self.run_replay()
        self.assertEqual(result['fixture_blobs'], {
            name: self.replay.git_blob(self.before[name])
            for name in ('recommendations.synthetic.csv', 'weights.json')})
        self.assertEqual(result['baseline_blob'], self.replay.git_blob(self.reference))

    def test_no_cached_calculator_module_is_reused(self):
        seen = []
        compile_source = builtins.compile
        def observed(source, *args, **kwargs):
            if isinstance(source, bytes) and source == self.source:
                seen.append(source)
            return compile_source(source, *args, **kwargs)
        with mock.patch.object(builtins, 'compile', observed):
            self.run_replay()
        self.assertEqual(seen, [self.source])

    def test_wrong_baseline_is_rejected_before_output(self):
        self.baseline.write_bytes(self.reference + b'\n# changed before capture\n')
        with self.assertRaisesRegex(ValueError, 'baseline does not match'):
            self.run_replay()
        self.assertFalse((self.root / 'out').exists())

    def test_wrong_fixture_is_rejected_before_output(self):
        for name in ('weights.json', 'recommendations.synthetic.csv'):
            with self.subTest(name=name):
                target = self.root / name
                target.write_bytes(self.before[name] + b'\n')
                with self.assertRaisesRegex(ValueError, 'synthetic fixture changed'):
                    self.run_replay()
                target.write_bytes(self.before[name])
                self.assertFalse((self.root / 'out').exists())

    def test_existing_output_preserved(self):
        out = self.root / 'out'
        out.mkdir()
        (out / 'earlier.txt').write_bytes(b'earlier analyst work')
        with self.assertRaisesRegex(ValueError, 'fresh output'):
            self.run_replay()
        self.assertEqual(list(out.iterdir()), [out / 'earlier.txt'])
        self.assertEqual((out / 'earlier.txt').read_bytes(), b'earlier analyst work')

    def test_normal_run_preserves_all_operator_inputs(self):
        self.run_replay()
        self.assertEqual(self.input_bytes(), self.before)

    def test_repeat_replay_has_identical_receipt(self):
        first, second = self.run_replay('first'), self.run_replay('second')
        self.assertEqual(first, second)
        self.assertEqual(first['seeded_comparisons_passed'], 250)
        self.assertEqual(first['unchanged_profile_record_rows'], 35)
        self.assertEqual(len(first['unchanged_output_files']), 7)
        self.assertEqual(first['optimized'], bool(sys.flags.optimize))

    def test_disk_receipt_matches_returned_receipt(self):
        result = self.run_replay()
        actual = json.loads((self.root / 'out' / 'replay_receipt.json').read_text())
        self.assertEqual(result, actual)


if __name__ == '__main__':
    unittest.main()
