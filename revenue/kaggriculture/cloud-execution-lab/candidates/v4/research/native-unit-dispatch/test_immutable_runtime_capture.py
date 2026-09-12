# SPDX-License-Identifier: Apache-2.0
"""Regression tests for KINETIC immutable validated/executed runtime custody."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run_kinetic_games as k


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class ImmutableRuntimeCapture(unittest.TestCase):
    def fixture(self, root: Path):
        files = {
            'mechanics.py': b'BASE = 1\n',
            'main.py': b'VALUE = "main"\n',
            'checks/reference/evaluator/loader.py': b'VALUE = "loader"\n',
            'checks/reference/engine/kaggriculture.py': b'VALUE = "engine"\n',
            'checks/reference/engine/kaggriculture.json': b'{"name":"engine"}\n',
            'checks/reference/engine/utils.py': b'VALUE = "utils"\n',
        }
        for name, raw in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        manifest = {'runtime': {name: {'sha256': _sha(raw)} for name, raw in files.items()}}
        manifest_raw = (json.dumps(manifest, sort_keys=True, separators=(',', ':')) + '\n').encode()
        (root / 'SOURCE.json').write_bytes(manifest_raw)
        engine_pins = {
            name: k.composer.git_blob(files[name])
            for name in k.ENGINE_GIT_BLOBS
        }
        return manifest_raw, files, engine_pins

    def patches(self, manifest_raw, files, engine_pins):
        return patch.multiple(
            k,
            SOURCE_SHA256=_sha(manifest_raw),
            ENGINE_GIT_BLOBS=engine_pins,
        ), patch.object(k.composer, 'BASE_BLOB', k.composer.git_blob(files['mechanics.py']))

    def test_path_replacement_after_capture_cannot_change_materialized_execution_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'root'; root.mkdir()
            manifest_raw, files, engine_pins = self.fixture(root)
            outer, base = self.patches(manifest_raw, files, engine_pins)
            with outer, base:
                captured_manifest, captured = k.capture_runtime(root)
                (root / 'main.py').write_bytes(b'VALUE = "reopened"\n')
                (root / 'mechanics.py').write_bytes(b'MUTATED = True\n')
                frozen = Path(d) / 'frozen'
                k.materialize_runtime(frozen, captured_manifest, captured)
            self.assertEqual(files['main.py'], (frozen / 'main.py').read_bytes())
            self.assertEqual(files['mechanics.py'], (frozen / 'mechanics.py').read_bytes())
            self.assertEqual(manifest_raw, (frozen / 'SOURCE.json').read_bytes())

    def test_candidate_mechanics_override_is_exact_and_only_for_mechanics(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); manifest_raw, files, engine_pins = self.fixture(root)
            candidate = b'CANDIDATE = 1\n'
            (root / 'mechanics.py').write_bytes(candidate)
            outer, base = self.patches(manifest_raw, files, engine_pins)
            with outer, base:
                captured_manifest, captured = k.capture_runtime(root, _sha(candidate))
                self.assertEqual(candidate, captured['mechanics.py'])
                self.assertEqual(manifest_raw, captured_manifest)
                with self.assertRaisesRegex(ValueError, 'mechanics.py'):
                    k.capture_runtime(root, _sha(b'wrong'))
                (root / 'main.py').write_bytes(b'DRIFT = 1\n')
                with self.assertRaisesRegex(ValueError, 'main.py'):
                    k.capture_runtime(root, _sha(candidate))

    def test_manifest_drift_fails_before_runtime_authority(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); manifest_raw, files, engine_pins = self.fixture(root)
            outer, base = self.patches(manifest_raw, files, engine_pins)
            with outer, base:
                (root / 'SOURCE.json').write_text('{}\n')
                with self.assertRaisesRegex(ValueError, 'SOURCE manifest'):
                    k.capture_runtime(root)

    def test_unsafe_runtime_member_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = {'runtime': {'../escape.py': {'sha256': _sha(b'x')}}}
            raw = (json.dumps(manifest, sort_keys=True, separators=(',', ':')) + '\n').encode()
            (root / 'SOURCE.json').write_bytes(raw)
            with patch.object(k, 'SOURCE_SHA256', _sha(raw)):
                with self.assertRaisesRegex(ValueError, 'Unsafe runtime member'):
                    k.capture_runtime(root)

    def test_symlinked_runtime_member_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'root'; root.mkdir()
            manifest_raw, files, engine_pins = self.fixture(root)
            outside = Path(d) / 'outside.py'; outside.write_bytes(files['main.py'])
            (root / 'main.py').unlink(); (root / 'main.py').symlink_to(outside)
            outer, base = self.patches(manifest_raw, files, engine_pins)
            with outer, base:
                with self.assertRaisesRegex(ValueError, 'Unsafe runtime input: main.py'):
                    k.capture_runtime(root)


if __name__ == '__main__':
    unittest.main()
