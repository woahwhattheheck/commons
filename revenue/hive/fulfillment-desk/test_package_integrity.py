"""Hostile package-integrity and file-custody tests for Parcel."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile
import bundle

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT.parent / 'intake-crm-workflow'
FIELDS = ('name', 'email', 'phone', 'address', 'service', 'preferred_date', 'notes')


def deployment():
    mapping = {field: field for field in FIELDS}
    return {
        'format': 'parcel.intake-handoff',
        'version': 1,
        'orderId': 'integrity-test',
        'specRevision': 1,
        'agency': 'Synthetic Agency',
        'client': 'Synthetic Client',
        'title': 'Client intake',
        'support': 'support@example.invalid',
        'brand': '#315c4b',
        'preset': 'client-intake',
        'scope': 'Synthetic scope only.',
        'fieldMapping': mapping,
        'tasks': ['Review intake', 'Assign owner', 'Record follow-up'],
        'exampleIntake': {
            'id': 'integrity-test-smoke-v1',
            'payload': {
                'name': 'Example Client',
                'email': 'example@example.invalid',
                'phone': '555-0100',
                'address': 'Synthetic address',
                'service': 'New client enquiry',
                'preferred_date': '',
                'notes': 'Synthetic only.',
            },
        },
        'recordedInstallation': False,
        'checklist': [],
        'quote': {
            'setup': 90000,
            'monthly': 0,
            'firstMonth': 90000,
            'currency': 'USD',
            'taxIncluded': False,
            'paymentRecorded': False,
        },
    }


def load_launcher(path: Path):
    spec = importlib.util.spec_from_file_location('parcel_integrity_test_launcher', path)
    if spec is None or spec.loader is None:
        raise AssertionError('could not load launcher')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PackageIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input = self.root / 'deployment.json'
        self.output = self.root / 'package.zip'
        self.package = self.root / 'package'
        self.input.write_text(json.dumps(deployment()), encoding='utf-8')

    def build_unpack(self):
        result = bundle.build(
            self.input,
            RUNNER,
            self.output,
            '9f216e50135948488cb2d95dfaaca337b490d3f5',
        )
        with zipfile.ZipFile(self.output) as archive:
            archive.extractall(self.package)
        return result, load_launcher(self.package / 'run.py')

    def test_manifest_enforces_immutable_members_before_workflow_load(self):
        _, launcher = self.build_unpack()
        config = launcher.verify_package(self.package)
        self.assertEqual(config['format'], 'parcel.intake-handoff')
        for name in ('workflow.py', 'index.html', 'parcel.json', 'example-intake.json'):
            with self.subTest(name=name):
                original = (self.package / name).read_bytes()
                (self.package / name).write_bytes(original + b'\n# tampered\n')
                with self.assertRaisesRegex(ValueError, 'integrity mismatch'):
                    launcher.verify_package(self.package)
                (self.package / name).write_bytes(original)
                launcher.verify_package(self.package)


    def test_verified_workflow_generation_is_not_reopened(self):
        _, launcher = self.build_unpack()
        config, verified = launcher.verify_package(self.package, include_bytes=True)
        original = verified['workflow.py']
        (self.package / 'workflow.py').write_text(
            "raise RuntimeError('replacement must not execute')\n",
            encoding='utf-8',
        )
        module = launcher._load_workflow_bytes(original, self.package / 'workflow.py')
        self.assertTrue(callable(module.main))
        self.assertEqual(config['agency'], 'Synthetic Agency')

    def test_operator_config_remains_editable(self):
        _, launcher = self.build_unpack()
        (self.package / 'config.local.json').write_text(
            json.dumps({'mapping': {field: field for field in FIELDS}, 'endpoint': 'https://example.invalid/receiver'}),
            encoding='utf-8',
        )
        self.assertEqual(launcher.verify_package(self.package)['agency'], 'Synthetic Agency')

    def test_manifest_inventory_cannot_reclassify_workflow_as_editable(self):
        self.build_unpack()
        path = self.package / 'MANIFEST.json'
        raw = json.loads(path.read_text(encoding='utf-8'))
        raw['runtimeImmutable'].remove('workflow.py')
        raw['operatorEditable'].append('workflow.py')
        path.write_text(json.dumps(raw), encoding='utf-8')
        launcher = load_launcher(self.package / 'run.py')
        with self.assertRaisesRegex(ValueError, 'editable-file contract'):
            launcher.verify_package(self.package)

    def test_duplicate_keys_and_nonfinite_deployment_json_fail_closed(self):
        for label, source in (
            ('duplicate', '{"format":"parcel.intake-handoff","format":"parcel.intake-handoff"}'),
            ('nan', '{"x":NaN}'),
        ):
            with self.subTest(label=label):
                self.input.write_text(source, encoding='utf-8')
                with self.assertRaises(ValueError):
                    bundle.build(self.input, RUNNER, self.root / f'{label}.zip')
                self.assertFalse((self.root / f'{label}.zip').exists())

    def test_symlink_deployment_and_runner_sources_are_refused(self):
        if not hasattr(os, 'symlink'):
            self.skipTest('symlinks unavailable')
        real_input = self.root / 'real.json'
        real_input.write_text(json.dumps(deployment()), encoding='utf-8')
        linked_input = self.root / 'linked.json'
        linked_input.symlink_to(real_input)
        with self.assertRaises(OSError):
            bundle.build(linked_input, RUNNER, self.root / 'linked-input.zip')

        runner = self.root / 'runner'
        runner.mkdir()
        (runner / 'index.html').write_bytes((RUNNER / 'index.html').read_bytes())
        (runner / 'workflow-real.py').write_bytes((RUNNER / 'workflow.py').read_bytes())
        (runner / 'workflow.py').symlink_to(runner / 'workflow-real.py')
        with self.assertRaises(OSError):
            bundle.build(real_input, runner, self.root / 'linked-runner.zip')

    def test_same_inode_mutation_during_read_is_detected_even_if_mtime_restored(self):
        target = self.root / 'changing.bin'
        target.write_bytes(b'a' * 140000)
        original = target.stat()
        real_read = bundle.os.read
        touched = False

        def racing_read(fd, size):
            nonlocal touched
            data = real_read(fd, size)
            if data and not touched:
                touched = True
                with target.open('r+b') as stream:
                    stream.seek(100000)
                    stream.write(b'b')
                    stream.flush()
                    os.fsync(stream.fileno())
                os.utime(target, ns=(original.st_atime_ns, original.st_mtime_ns))
            return data

        with mock.patch.object(bundle.os, 'read', side_effect=racing_read):
            with self.assertRaisesRegex(ValueError, 'changed while it was being read'):
                bundle.read_regular(target, 'changing input', 200000)

    def test_output_path_replacement_is_not_reported_or_deleted(self):
        real_zip = bundle.zipfile.ZipFile
        output = self.output

        class ReplaceOnExit:
            def __init__(self, fileobj, *args, **kwargs):
                self.inner = real_zip(fileobj, *args, **kwargs)

            def __enter__(self):
                return self.inner

            def __exit__(self, exc_type, exc, tb):
                result = self.inner.__exit__(exc_type, exc, tb)
                try:
                    output.unlink()
                except FileNotFoundError:
                    pass
                output.write_bytes(b'foreign replacement')
                return result

        with mock.patch.object(bundle.zipfile, 'ZipFile', ReplaceOnExit):
            with self.assertRaisesRegex(RuntimeError, 'no longer names'):
                bundle.build(self.input, RUNNER, output)
        self.assertEqual(output.read_bytes(), b'foreign replacement')

    def test_result_hash_is_from_created_inode(self):
        result, _ = self.build_unpack()
        self.assertEqual(result['bytes'], self.output.stat().st_size)
        self.assertEqual(result['sha256'], hashlib.sha256(self.output.read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
