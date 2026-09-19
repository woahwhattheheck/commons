#!/usr/bin/env python3
"""Independent UIOWA-108 I/O regressions; fictional inputs and no network.

Run from the repository root after applying output_preservation.patch:
    python -B reviews/uiowa108-output-preservation-r3/regressions.py
    python -B -O reviews/uiowa108-output-preservation-r3/regressions.py

UIOWA108_COMPONENT may select another exact component directory for replay.

The module loader captures source once and temporarily binds only its own
scenario dependency. It does not inherit unrelated generic scenario modules.
All child CLI processes propagate the parent's optimization mode.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(os.environ.get("UIOWA108_COMPONENT", str(
    Path(__file__).resolve().parents[2] / "revenue/uiowa_rfq_18649_contractor_transition"))).resolve()
NAMES = ('transition_items.csv', 'transition_report.json', 'transition_report.md')
SOURCE_BYTES = {name: (HERE / name).read_bytes() for name in ('scenario.py', 'transition.py')}


def _load():
    modules = {}
    for name in ('scenario', 'transition'):
        path = HERE / (name + '.py')
        module = importlib.util.module_from_spec(importlib.util.spec_from_file_location('_uiowa108_r3_' + name, path))
        if name == 'transition':
            missing = object()
            before = sys.modules.get('scenario', missing)
            sys.modules['scenario'] = modules['scenario']
            try:
                exec(compile(SOURCE_BYTES[name + '.py'], str(path), 'exec'), module.__dict__)
            finally:
                if before is missing:
                    sys.modules.pop('scenario', None)
                else:
                    sys.modules['scenario'] = before
        else:
            exec(compile(SOURCE_BYTES[name + '.py'], str(path), 'exec'), module.__dict__)
        modules[name] = module
    return modules['transition']


engine = _load()


def packet():
    return {
        'packet_id': 'SYNTHETIC-IO-REVIEW',
        'transition': {'departing_ref': 'SYN-PERSON-001'},
        'people': [
            {'id': 'SYN-PERSON-001', 'role': 'contractor', 'employment_type': 'contractor', 'service': 'ESS', 'synthetic': True},
            {'id': 'SYN-PERSON-002', 'role': 'lead', 'employment_type': 'staff', 'service': 'ESS', 'synthetic': True}],
        'applications': [{'id': 'SYN-APP-001', 'name': 'Fictional application', 'service': 'ESS',
                          'owner_ref': 'SYN-PERSON-001', 'successor_ref': 'SYN-PERSON-002', 'synthetic': True}],
        'access_changes': [{'id': 'SYN-CHG-001', 'subject_ref': 'SYN-PERSON-001', 'target_ref': 'SYN-APP-001',
                            'action': 'REASSIGN_OWNER', 'status': 'COMPLETED', 'completed_at': '2026-09-19',
                            'evidence_ref': 'synthetic://review/one', 'synthetic': True}],
    }


def _blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


class OutputPreservation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source.json'
        self.source.write_text(json.dumps(packet()), encoding='utf-8')
        self.original = self.source.read_bytes()
        self.out = self.root / 'out'
        self.out.mkdir()

    def cli(self, source=None, out=None):
        command = [sys.executable, '-B']
        if sys.flags.optimize:
            command.append('-' + 'O' * sys.flags.optimize)
        command += [str(HERE / 'transition.py'), '--input', str(source or self.source), '--outdir', str(out or self.out)]
        return subprocess.run(command, capture_output=True, text=True, timeout=15)

    def assert_controlled(self, result):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertNotIn('wrote 3 files', result.stdout)

    def snapshot(self):
        return {p.name: p.read_bytes() for p in self.out.iterdir() if p.is_file()}

    def test_closed_success_keeps_source_and_three_artifacts(self):
        p = self.cli()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(set(self.snapshot()), set(NAMES))
        self.assertTrue(json.loads((self.out / NAMES[1]).read_text())['transition_closed'])

    def test_open_success_retains_exit_one(self):
        data = packet(); data['access_changes'] = []
        self.source.write_text(json.dumps(data))
        p = self.cli()
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertFalse(json.loads((self.out / NAMES[1]).read_text())['transition_closed'])
        self.assertEqual(set(self.snapshot()), set(NAMES))

    def test_original_fixture_stays_two_two_two(self):
        fixture = HERE / 'fixtures/contractor_transition.json'
        self.assertEqual(_blob(fixture.read_bytes()), '0939e7cd6c72920acc7a576d9e2070390c0b66a9')
        p = self.cli(source=fixture)
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertEqual(json.loads((self.out / NAMES[1]).read_text())['counts'],
                         {'COMPLETED': 2, 'UNRESOLVED_OWNERSHIP': 2, 'NO_EVIDENCE': 2})

    def test_existing_empty_directory_supported(self):
        self.assertTrue(self.out.is_dir())
        self.assertEqual(self.cli().returncode, 0)

    def test_missing_parent_directories_supported(self):
        out = self.root / 'new/nested/out'
        self.assertEqual(self.cli(out=out).returncode, 0)
        self.assertEqual({p.name for p in out.iterdir()}, set(NAMES))

    def test_unrelated_existing_file_preserved(self):
        sentinel = self.out / 'notes.txt'; sentinel.write_bytes(b'keep\x00\r\n')
        self.assertEqual(self.cli().returncode, 0)
        self.assertEqual(sentinel.read_bytes(), b'keep\x00\r\n')

    def test_second_run_refused_without_changing_first(self):
        self.assertEqual(self.cli().returncode, 0)
        before = self.snapshot()
        self.assert_controlled(self.cli())
        self.assertEqual(self.snapshot(), before)

    def test_existing_artifact_refused_before_other_writes(self):
        for name in NAMES:
            with self.subTest(name=name):
                target = self.out / name; target.write_bytes(b'PREVIOUS\r\n')
                before = self.snapshot()
                self.assert_controlled(self.cli())
                self.assertEqual(self.snapshot(), before)
                target.unlink()

    def test_each_direct_input_alias_preserved(self):
        for name in NAMES:
            with self.subTest(name=name):
                target = self.out / name; target.write_bytes(self.original)
                self.assert_controlled(self.cli(source=target))
                self.assertEqual(self.snapshot(), {name: self.original})
                target.unlink()

    def test_each_symlink_input_alias_preserved(self):
        for name in NAMES:
            with self.subTest(name=name):
                target = self.out / name; target.symlink_to(self.source)
                self.assert_controlled(self.cli())
                self.assertTrue(target.is_symlink())
                self.assertEqual(self.source.read_bytes(), self.original)
                self.assertEqual(set(self.snapshot()), {name})
                target.unlink()

    def test_each_hardlink_input_alias_preserved(self):
        for name in NAMES:
            with self.subTest(name=name):
                target = self.out / name; target.hardlink_to(self.source)
                self.assert_controlled(self.cli())
                self.assertEqual(self.source.read_bytes(), self.original)
                self.assertEqual(set(self.snapshot()), {name})
                target.unlink()

    def test_each_dangling_symlink_preserved(self):
        for name in NAMES:
            with self.subTest(name=name):
                target = self.out / name; target.symlink_to(self.root / 'absent')
                self.assert_controlled(self.cli())
                self.assertTrue(target.is_symlink())
                self.assertEqual({p.name for p in self.out.iterdir()}, {name})
                self.assertFalse((self.root / 'absent').exists())
                target.unlink()

    def test_directory_at_output_name_preserved(self):
        target = self.out / NAMES[1]; target.mkdir()
        self.assert_controlled(self.cli())
        self.assertEqual(list(self.out.iterdir()), [target])

    def test_outdir_file_is_controlled_error_not_open_outcome(self):
        self.out.rmdir(); self.out.write_bytes(b'SENTINEL')
        self.assert_controlled(self.cli())
        self.assertEqual(self.out.read_bytes(), b'SENTINEL')

    def test_outdir_equal_input_keeps_source(self):
        self.assert_controlled(self.cli(out=self.source))
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_unsafe_content_still_writes_nothing(self):
        data = packet(); data['people'][0]['synthetic'] = False
        self.source.write_text(json.dumps(data))
        p = self.cli()
        self.assertEqual(p.returncode, 3)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_malformed_input_still_writes_nothing(self):
        self.source.write_text('{ invalid')
        self.assert_controlled(self.cli())
        self.assertEqual(list(self.out.iterdir()), [])

    def test_render_encoding_failure_precedes_all_artifacts(self):
        data = packet(); data['applications'][0]['name'] = 'synthetic-\ud800'
        self.source.write_text(json.dumps(data))
        self.assert_controlled(self.cli())
        self.assertEqual(list(self.out.iterdir()), [])

    def test_partial_write_failure_rolls_back_reserved_set(self):
        real_write = os.write; calls = []
        def fail(fd, data):
            if calls:
                raise OSError('synthetic disk error')
            calls.append(fd)
            return real_write(fd, data[:7])
        with mock.patch.object(engine.os, 'write', side_effect=fail):
            with self.assertRaisesRegex(OSError, 'synthetic disk error'):
                engine.publish_artifacts(engine.build(packet())[0], self.out)
        self.assertEqual(list(self.out.iterdir()), [])
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_fsync_failure_rolls_back_reserved_set(self):
        with mock.patch.object(engine.os, 'fsync', side_effect=OSError('synthetic sync error')):
            with self.assertRaisesRegex(OSError, 'synthetic sync error'):
                engine.publish_artifacts(engine.build(packet())[0], self.out)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_second_reservation_failure_removes_first(self):
        real_open = os.open
        def fail(path, *args):
            if str(path).endswith(NAMES[1]):
                raise OSError('synthetic reservation error')
            return real_open(path, *args)
        with mock.patch.object(engine.os, 'open', side_effect=fail):
            with self.assertRaisesRegex(OSError, 'synthetic reservation error'):
                engine.publish_artifacts(engine.build(packet())[0], self.out)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_concurrent_entry_survives_exclusive_reservation(self):
        real_open = os.open
        def race(path, *args):
            if str(path).endswith(NAMES[1]):
                Path(path).write_bytes(b'OTHER-WRITER')
            return real_open(path, *args)
        with mock.patch.object(engine.os, 'open', side_effect=race):
            with self.assertRaises(FileExistsError):
                engine.publish_artifacts(engine.build(packet())[0], self.out)
        self.assertEqual(self.snapshot(), {NAMES[1]: b'OTHER-WRITER'})

    def test_short_writes_preserve_all_bytes(self):
        real_write = os.write
        with mock.patch.object(engine.os, 'write', side_effect=lambda fd, data: real_write(fd, data[:3])):
            engine.publish_artifacts(engine.build(packet())[0], self.out)
        self.assertEqual(self.snapshot(), engine._artifact_payloads(engine.build(packet())[0]))

    def test_zero_write_is_controlled_failure_not_infinite_loop(self):
        with mock.patch.object(engine.os, 'write', return_value=0):
            with self.assertRaisesRegex(OSError, 'no progress'):
                engine.publish_artifacts(engine.build(packet())[0], self.out)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_replaced_output_is_not_deleted_during_rollback(self):
        first = self.out / NAMES[0]
        def replace(fd, data):
            first.unlink(); first.write_bytes(b'OTHER-WRITER')
            raise OSError('synthetic replacement')
        with mock.patch.object(engine.os, 'write', side_effect=replace):
            with self.assertRaisesRegex(OSError, 'cleanup incomplete'):
                engine.publish_artifacts(engine.build(packet())[0], self.out)
        self.assertEqual(self.snapshot(), {NAMES[0]: b'OTHER-WRITER'})

    def test_cleanup_failure_is_reported_not_called_success(self):
        with mock.patch.object(engine.os, 'write', side_effect=OSError('synthetic disk error')):
            with mock.patch.object(engine.os, 'unlink', side_effect=PermissionError('synthetic cleanup refusal')):
                with self.assertRaisesRegex(OSError, 'cleanup incomplete'):
                    engine.publish_artifacts(engine.build(packet())[0], self.out)
        self.assertEqual(set(self.snapshot()), set(NAMES))

    def test_main_maps_output_failure_to_two(self):
        with mock.patch.object(engine, 'publish_artifacts', side_effect=OSError('synthetic output error')):
            with mock.patch.object(engine.sys, 'stderr') as stderr:
                self.assertEqual(engine.main(['--input', str(self.source), '--outdir', str(self.out)]), 2)
                self.assertIn('cannot publish output', stderr.write.call_args.args[0])
        self.assertEqual(list(self.out.iterdir()), [])

    def test_normal_and_optimized_cli_bytes_match(self):
        p = self.cli(); self.assertEqual(p.returncode, 0)
        out2 = self.root / 'optimized'
        q = subprocess.run([sys.executable, '-B', '-O', str(HERE / 'transition.py'), '--input', str(self.source), '--outdir', str(out2)], capture_output=True, text=True, timeout=15)
        self.assertEqual(q.returncode, 0, q.stderr)
        self.assertEqual(self.snapshot(), {p.name: p.read_bytes() for p in out2.iterdir()})

    def test_captured_sources_unchanged_during_run(self):
        for name, captured in SOURCE_BYTES.items():
            self.assertEqual((HERE / name).read_bytes(), captured)


if __name__ == '__main__':
    unittest.main(verbosity=2)
