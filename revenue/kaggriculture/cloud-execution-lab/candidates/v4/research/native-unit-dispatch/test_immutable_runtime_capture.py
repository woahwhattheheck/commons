# SPDX-License-Identifier: Apache-2.0
"""Regression tests for KINETIC immutable validated/executed runtime custody."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
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
            name: k.git_blob(files[name])
            for name in k.ENGINE_GIT_BLOBS
        }
        return manifest_raw, files, engine_pins

    def control_fixture(self, root: Path):
        source_root = Path(k.__file__).resolve().parent
        files = {name: (source_root / name).read_bytes() for name in k.CONTROL_FILES}
        for name, raw in files.items():
            (root / name).write_bytes(raw)
        return files

    def patches(self, manifest_raw, files, engine_pins):
        return patch.multiple(
            k,
            SOURCE_SHA256=_sha(manifest_raw),
            ENGINE_GIT_BLOBS=engine_pins,
        ), patch.object(k, 'BASE_MECHANICS_BLOB', k.git_blob(files['mechanics.py']))

    def probe_control(self, root: Path, expected_digest: str = '0' * 64,
                      expected_runner_git_blob: str | None = None):
        output = root / 'probe.json'
        if expected_runner_git_blob is None:
            expected_runner_git_blob = k.git_blob((root / 'run_kinetic_games.py').read_bytes())
        proc = subprocess.run(
            [
                sys.executable,
                '-B',
                str(root / 'run_kinetic_games.py'),
                '--native-root',
                str(root / 'unused-native-root'),
                '--output',
                str(output),
                '--expected-runner-git-blob',
                expected_runner_git_blob,
                '--control-probe',
                '--expected-control-bundle-sha256',
                expected_digest,
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        return proc, output

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

    def test_control_bundle_survives_repo_runner_replacement_and_executes_frozen_program(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            mutable = base / 'mutable-control'; mutable.mkdir()
            original = self.control_fixture(mutable)
            expected_runner = k.git_blob(original['run_kinetic_games.py'])
            captured, digest = k.capture_control_bundle(mutable, expected_runner)
            self.assertEqual(original, captured)

            # After parent capture, replace the repository runner. Children must
            # never reopen this path.
            (mutable / 'run_kinetic_games.py').write_text(
                'raise SystemExit("MUTATED REPO RUNNER EXECUTED")\n'
            )
            frozen = base / 'frozen-control'
            k.materialize_control_bundle(frozen, captured)
            output = base / 'probe.json'
            proc = subprocess.run(
                [
                    sys.executable,
                    '-B',
                    str(frozen / 'run_kinetic_games.py'),
                    '--native-root',
                    str(base / 'unused-native-root'),
                    '--output',
                    str(output),
                    '--expected-runner-git-blob',
                    expected_runner,
                    '--control-probe',
                    '--expected-control-bundle-sha256',
                    digest,
                ],
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            receipt = json.loads(output.read_text())
            self.assertEqual(receipt['executed_control_bundle_sha256'], digest)
            self.assertEqual(receipt['executed_control_runner_blob'], expected_runner)
            self.assertEqual(
                (frozen / 'run_kinetic_games.py').read_bytes(),
                original['run_kinetic_games.py'],
            )

    def test_external_runner_pin_rejects_pre_capture_repo_runner_replacement(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = self.control_fixture(root)
            expected_runner = k.git_blob(original['run_kinetic_games.py'])
            (root / 'run_kinetic_games.py').write_text(
                '# valid but poisoned replacement\nraise SystemExit("POISONED")\n'
            )
            with self.assertRaisesRegex(ValueError, 'Unverified control runner'):
                k.capture_control_bundle(root, expected_runner)
            with self.assertRaisesRegex(ValueError, 'Invalid expected runner Git blob'):
                k.capture_control_bundle(root, 'not-an-external-pin')

    def test_control_helper_drift_fails_closed_before_child_launch(self):
        for name in ('compose_kinetic.py', 'check_kinetic.py'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                original = self.control_fixture(root)
                expected_runner = k.git_blob(original['run_kinetic_games.py'])
                (root / name).write_bytes(b'DRIFT = True\n')
                with self.assertRaisesRegex(ValueError, f'Unverified control input: {name}'):
                    k.capture_control_bundle(root, expected_runner)

    def test_unverified_composer_cannot_execute_before_authentication(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = self.control_fixture(root)
            expected_runner = k.git_blob(original['run_kinetic_games.py'])
            marker = root / 'composer-executed'
            (root / 'compose_kinetic.py').write_text(
                'from pathlib import Path\n'
                f'Path({str(marker)!r}).write_text("EXECUTED")\n'
                f'BASE_BLOB = {k.BASE_MECHANICS_BLOB!r}\n'
                'def git_blob(raw): return "d34362e98277c930b7b28519f2892bea758b3878"\n'
                'def compose(source): return source\n'
            )
            proc, _ = self.probe_control(root, expected_runner_git_blob=expected_runner)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('Unverified control input: compose_kinetic.py', proc.stderr)
            self.assertFalse(marker.exists(), proc.stdout + proc.stderr)

    def test_unverified_checker_cannot_execute_before_authentication(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = self.control_fixture(root)
            expected_runner = k.git_blob(original['run_kinetic_games.py'])
            marker = root / 'checker-executed'
            (root / 'check_kinetic.py').write_text(
                'from pathlib import Path\n'
                f'Path({str(marker)!r}).write_text("EXECUTED")\n'
                'def imported(*args): raise RuntimeError("attacker checker executed")\n'
            )
            proc, _ = self.probe_control(root, expected_runner_git_blob=expected_runner)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('Unverified control input: check_kinetic.py', proc.stderr)
            self.assertFalse(marker.exists(), proc.stdout + proc.stderr)

    def test_captured_composer_is_executed_from_authenticated_bytes_not_reopened_path(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = self.control_fixture(root)
            expected_runner = k.git_blob(original['run_kinetic_games.py'])
            captured, _ = k.capture_control_bundle(root, expected_runner)
            marker = root / 'reopened-composer-executed'
            (root / 'compose_kinetic.py').write_text(
                'from pathlib import Path\n'
                f'Path({str(marker)!r}).write_text("EXECUTED")\n'
                'raise RuntimeError("reopened composer executed")\n'
            )
            module = k.load_captured_composer(captured['compose_kinetic.py'])
            self.assertEqual(module.BASE_BLOB, k.BASE_MECHANICS_BLOB)
            self.assertTrue(callable(module.compose))
            self.assertFalse(marker.exists())


if __name__ == '__main__':
    unittest.main()
