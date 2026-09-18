"""Root battery integration for the canonical offline bundle recovery CLI.

The broader pytest matrix lives in tests/test_git_bundle_inspect.py. This file
needs only the standard library (plus Git for two fixture tests) and therefore
runs under the existing root test_*.py discovery without workflow changes.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

from host.git_bundle_inspect import BundleError, Limits, inspect_bundle

ROOT = Path(__file__).resolve().parent
CLI = ROOT / 'host' / 'git_bundle_inspect.py'


def oid(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def packed(kind: int, data: bytes, base: bytes = b'') -> bytes:
    size = len(data)
    header = bytearray([(kind << 4) | (size & 15)])
    size >>= 4
    while size:
        header[-1] |= 128
        header.append(size & 127)
        size >>= 7
    return bytes(header) + base + zlib.compress(data)


def fixture(entries: list[bytes], tip: str, prerequisite: str | None = None) -> bytes:
    header = b'# v2 git bundle\n'
    if prerequisite:
        header += b'-' + prerequisite.encode() + b' fixture prerequisite\n'
    header += tip.encode() + b' refs/heads/fixture\n\n'
    pack = b'PACK' + struct.pack('>II', 2, len(entries)) + b''.join(entries)
    return header + pack + hashlib.sha1(pack).digest()


class RootRecoveryCI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = b'root battery fixture\n'
        self.bundle = fixture([packed(3, self.payload)], oid(self.payload))
        self.path = self.root / 'input.bundle'
        self.path.write_bytes(self.bundle)

    def command(self, path: Path | None = None, *arguments: str):
        # -S proves that CLI integration does not depend on site packages.
        return subprocess.run([sys.executable, '-S', str(CLI), str(path or self.path), *arguments],
                              cwd=self.root, capture_output=True, timeout=15)

    def test_cli_binary_and_base64_transport(self):
        encoded = self.root / 'input.base64'
        encoded.write_bytes(base64.encodebytes(self.bundle))
        digest = hashlib.sha256(self.bundle).hexdigest()
        for path, flags in ((self.path, []), (encoded, ['--base64'])):
            with self.subTest(flags=flags):
                result = self.command(path, *flags, '--sha256', digest)
                self.assertEqual(result.returncode, 0, result.stderr)
                manifest = json.loads(result.stdout)
                self.assertEqual(manifest['bundle_sha256'], digest)
                self.assertEqual(manifest['resolved_pack_objects'], 1)
                self.assertFalse(manifest['git_restore_verified'])

    def test_cli_hash_mismatch_does_not_export(self):
        output = self.root / 'rejected'
        result = self.command(None, '--sha256', '0' * 64, '--output', str(output))
        self.assertEqual(result.returncode, 2)
        self.assertIn(b'SHA256 does not match', result.stderr)
        self.assertFalse(output.exists())

    def test_export_refuses_existing_directory(self):
        output = self.root / 'recovered'
        result = self.command(None, '--output', str(output))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((output / 'objects' / (oid(self.payload) + '.blob')).read_bytes(), self.payload)
        original = (output / 'manifest.json').read_bytes()
        result = self.command(None, '--output', str(output))
        self.assertEqual(result.returncode, 2)
        self.assertEqual((output / 'manifest.json').read_bytes(), original)

    def test_partial_exit_and_explicit_base_resolution(self):
        # A tiny valid delta inserts 'abd' after declaring a three-byte base.
        base = b'abc'
        changed = b'abd'
        thin = fixture([packed(3, self.payload), packed(7, b'\x03\x03\x03abd', bytes.fromhex(oid(base)))],
                       oid(changed), 'a' * 40)
        path = self.root / 'thin.bundle'
        path.write_bytes(thin)
        output = self.root / 'partial'
        result = self.command(path, '--fail-on-unresolved', '--output', str(output))
        self.assertEqual(result.returncode, 3, result.stderr)
        manifest = json.loads(result.stdout)
        self.assertEqual(manifest['unresolved_pack_objects'], 1)
        self.assertFalse(manifest['git_restore_verified'])
        self.assertEqual((output / 'objects' / (oid(self.payload) + '.blob')).read_bytes(), self.payload)
        base_path = self.root / 'base.raw'
        base_path.write_bytes(base)
        result = self.command(path, '--base-object', 'blob:' + str(base_path), '--fail-on-unresolved')
        self.assertEqual(result.returncode, 0, result.stderr)
        resolved = json.loads(result.stdout)
        self.assertEqual(resolved['unresolved_pack_objects'], 0)
        self.assertEqual(resolved['prerequisites'][0]['oid'], 'a' * 40)
        self.assertFalse(resolved['git_restore_verified'])

    def test_corrupt_bundle_never_exports(self):
        corrupt = bytearray(self.bundle)
        corrupt[-1] ^= 1
        self.path.write_bytes(corrupt)
        output = self.root / 'corrupt-output'
        result = self.command(None, '--output', str(output))
        self.assertEqual(result.returncode, 2)
        self.assertIn(b'checksum', result.stderr)
        self.assertFalse(output.exists())

    def test_library_limits_are_enforced(self):
        with self.assertRaises(BundleError):
            inspect_bundle(self.bundle, limits=Limits(input_bytes=len(self.bundle) - 1))
        with self.assertRaises(BundleError):
            inspect_bundle(self.bundle, limits=Limits(object_bytes=len(self.payload) - 1))
        with self.assertRaises(BundleError):
            inspect_bundle(self.bundle, limits=Limits(objects=0))

    def git(self, directory, *arguments):
        env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
        env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_AUTHOR_NAME='Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
                   GIT_COMMITTER_NAME='Fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid',
                   GIT_TERMINAL_PROMPT='0')
        return subprocess.run(['git', '-c', 'core.hooksPath=' + os.devnull, *arguments],
                              cwd=directory, env=env, capture_output=True, check=True,
                              timeout=15).stdout

    @unittest.skipUnless(shutil.which('git'), 'Git required for native fixture generation')
    def test_real_git_full_bundles_match_native_objects(self):
        for algorithm in ('sha1', 'sha256'):
            with self.subTest(algorithm=algorithm):
                repo = self.root / algorithm
                repo.mkdir()
                self.git(repo, 'init', '-q', '--object-format=' + algorithm)
                (repo / 'file.txt').write_bytes(self.payload)
                self.git(repo, 'add', '.')
                self.git(repo, 'commit', '-qm', 'root integration fixture')
                path = self.root / (algorithm + '.bundle')
                self.git(repo, 'bundle', 'create', str(path), '--all')
                manifest, objects = inspect_bundle(path.read_bytes())
                self.assertEqual(manifest['object_format'], algorithm)
                self.assertEqual(manifest['unresolved_pack_objects'], 0)
                self.assertFalse(manifest['git_restore_verified'])
                for object_id, (kind, data) in objects.items():
                    self.assertEqual(self.git(repo, 'cat-file', kind, object_id), data)

    @unittest.skipUnless(shutil.which('git'), 'Git required for native fixture generation')
    def test_real_incremental_prerequisite_is_preserved(self):
        repo = self.root / 'incremental'
        repo.mkdir()
        self.git(repo, 'init', '-q')
        (repo / 'old.txt').write_bytes(b'old fixture')
        self.git(repo, 'add', '.')
        self.git(repo, 'commit', '-qm', 'base')
        base = self.git(repo, 'rev-parse', 'HEAD').strip().decode()
        (repo / 'new.txt').write_bytes(self.payload)
        self.git(repo, 'add', '.')
        self.git(repo, 'commit', '-qm', 'head')
        path = self.root / 'incremental.bundle'
        self.git(repo, 'bundle', 'create', str(path), 'HEAD', '^' + base)
        manifest, objects = inspect_bundle(path.read_bytes())
        self.assertEqual(manifest['prerequisites'][0]['oid'], base)
        self.assertEqual(objects[oid(self.payload)], ('blob', self.payload))
        self.assertFalse(manifest['git_restore_verified'])


if __name__ == '__main__':
    unittest.main()
