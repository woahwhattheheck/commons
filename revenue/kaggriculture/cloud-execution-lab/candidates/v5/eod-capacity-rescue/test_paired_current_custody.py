#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
KG_ROOT = HERE.parents[3]
SPEC = importlib.util.spec_from_file_location('_eod_paired_current_custody', HERE / 'paired_current.py')
assert SPEC is not None and SPEC.loader is not None
paired = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(paired)


class EODPairedCurrentCustodyTests(unittest.TestCase):
    @property
    def canonical(self) -> Path:
        return KG_ROOT / paired.SHARED_REL

    def _copy_authority(self, root: Path) -> Path:
        target = root / paired.SHARED_REL
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.canonical, target)
        return target

    def test_canonical_shared_helper_matches_pinned_authority(self):
        module, authority = paired.load_pinned_shared(self.canonical, '_eod_custody_canonical')
        raw = self.canonical.read_bytes()
        self.assertEqual(authority['git_blob'], paired.PINNED_SHARED_BLOB)
        self.assertEqual(authority['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(authority['bytes'], len(raw))
        self.assertEqual(authority['path'], paired.SHARED_REL.as_posix())
        self.assertEqual(authority['load_mode'], 'single-read-authenticated-compile-exec')
        self.assertTrue(callable(module.digest))
        self.assertTrue(callable(module.archive_members))

    def test_regular_exact_copy_loads_with_same_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copied = self._copy_authority(root)
            module, authority = paired.load_pinned_shared(copied, '_eod_custody_copy')
            self.assertEqual(authority['git_blob'], paired.PINNED_SHARED_BLOB)
            self.assertEqual(authority['sha256'], hashlib.sha256(copied.read_bytes()).hexdigest())
            self.assertTrue(callable(module.snapshot_harness))

    def test_stable_tampered_helper_fails_before_output_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'kg'
            helper = self._copy_authority(root)
            helper.write_bytes(helper.read_bytes() + b'\n# stable evidence drift\n')
            output = Path(directory) / 'evidence'
            with self.assertRaisesRegex(ValueError, 'identity drift'):
                paired.prepare_shared_authority(root, output)
            self.assertFalse(output.exists())

    def test_symlink_helper_fails_before_output_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'kg'
            helper = root / paired.SHARED_REL
            helper.parent.mkdir(parents=True, exist_ok=True)
            output = Path(directory) / 'evidence'
            try:
                helper.symlink_to(self.canonical)
            except (OSError, NotImplementedError):
                self.skipTest('symlink creation is unavailable on this platform')
            with self.assertRaisesRegex(ValueError, 'regular file'):
                paired.prepare_shared_authority(root, output)
            self.assertFalse(output.exists())

    def test_existing_output_is_rejected_before_authority_load(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'kg'
            self._copy_authority(root)
            output = Path(directory) / 'evidence'
            output.mkdir()
            with self.assertRaises(FileExistsError):
                paired.prepare_shared_authority(root, output)


if __name__ == '__main__':
    unittest.main(verbosity=2)
