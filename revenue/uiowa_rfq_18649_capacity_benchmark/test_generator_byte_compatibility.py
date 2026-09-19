"""Independent byte-compatibility and output-reservation proof for UIOWA-095.

Golden outputs were executed from OP5-OBSIDIAN's original generator blob
6a21c5b6df263960c88bbc992d7bbfd78399bd4c, seed 7, before testing the repair.
OP5-MARROW retains deletion-finding credit; ZZ-CADMIUM-R72F owns its repair.
Complementary proof: ZZ-QUARTZLINE / GPT-6 Astra Pro. All files are synthetic
and confined to TemporaryDirectory fixtures. No historical timing is reminted.
This checks accidental output preservation, not malicious ancestor replacement.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import generate_collection as gen


GOLDEN_SEED7 = {'large': {'seed': 7,
           'summary': {'collection_bytes': 59076184,
                       'document_bytes': 55159768,
                       'documents_listed': 600,
                       'documents_on_disk': 599,
                       'evidence_rows': 10000,
                       'finding_rows': 3000,
                       'largest_document_bytes': 1430881,
                       'profile': 'large',
                       'recommendation_rows': 1200,
                       'report_chars': 631673,
                       'seed': 7,
                       'trace_rows': 3000},
           'tree': {'bytes': 59076184,
                    'files': 606,
                    'sha256': '2799d531543551318e028d71b4528738c8f397e3d5f4581ed970f15ca2785cdf'}},
 'medium': {'seed': 7,
            'summary': {'collection_bytes': 10675827,
                        'document_bytes': 9889456,
                        'documents_listed': 200,
                        'documents_on_disk': 199,
                        'evidence_rows': 2000,
                        'finding_rows': 600,
                        'largest_document_bytes': 715534,
                        'profile': 'medium',
                        'recommendation_rows': 240,
                        'report_chars': 122361,
                        'seed': 7,
                        'trace_rows': 600},
            'tree': {'bytes': 10675827,
                     'files': 206,
                     'sha256': 'f0499f517202c2d89ef83a9a12887c5bae5888e19d20a69921d940b744ed0ae9'}},
 'small': {'seed': 7,
           'summary': {'collection_bytes': 831654,
                       'document_bytes': 748583,
                       'documents_listed': 40,
                       'documents_on_disk': 39,
                       'evidence_rows': 200,
                       'finding_rows': 60,
                       'largest_document_bytes': 238232,
                       'profile': 'small',
                       'recommendation_rows': 24,
                       'report_chars': 12125,
                       'seed': 7,
                       'trace_rows': 60},
           'tree': {'bytes': 831654,
                    'files': 46,
                    'sha256': '8cdc987176cb7a8c14bb5e29bc8e3e9624f5fbfd758ccaaecc4ff9f20353c748'}}}
SCRIPT = Path(gen.__file__).resolve()
TINY = gen.Profile("compatibility-fixture", 12, 6, 4, 6, 4, 2, 2, 4)


def tree_digest(root: Path) -> dict:
    """Hash length-framed sorted relative POSIX paths and actual file bytes."""
    digest = hashlib.sha256()
    count = total = 0
    for path in sorted(root.rglob("*")):
        if path.is_file():
            name = path.relative_to(root).as_posix().encode("utf-8")
            body = path.read_bytes()
            digest.update(len(name).to_bytes(8, "big"))
            digest.update(name)
            digest.update(len(body).to_bytes(8, "big"))
            digest.update(body)
            count += 1
            total += len(body)
    return {"files": count, "bytes": total, "sha256": digest.hexdigest()}


class GeneratorByteCompatibility(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="uiowa095-compatibility-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def argv(self, target):
        # Optimized-suite child processes must actually run optimized Python.
        return [sys.executable, *(["-O"] if sys.flags.optimize else []),
                str(SCRIPT), "--profile", "small", "--seed", "7", "--out", str(target)]

    def test_every_file_and_summary_matches_original_at_all_three_sizes(self):
        for name, expected in GOLDEN_SEED7.items():
            with self.subTest(profile=name):
                target = self.root / name
                summary = gen.generate(target, gen.PROFILES[name], seed=7)
                self.assertEqual(expected["summary"], summary)
                self.assertEqual(expected["tree"], tree_digest(target))

    def test_real_cli_retains_complete_small_output(self):
        target = self.root / "cli"
        result = subprocess.run(self.argv(target), capture_output=True, text=True,
                                cwd=self.root, timeout=30, check=False)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stderr)
        self.assertEqual(GOLDEN_SEED7["small"]["summary"], json.loads(result.stdout))
        self.assertEqual(GOLDEN_SEED7["small"]["tree"], tree_digest(target))

    def test_two_real_cli_writers_leave_one_complete_collection(self):
        # Popen starts both before waiting; scheduler ordering is not asserted.
        # Three trials supplement, not replace, the deterministic collision below.
        for trial in range(3):
            with self.subTest(trial=trial):
                target = self.root / f"shared-{trial}"
                processes = []
                try:
                    for _ in range(2):
                        processes.append(subprocess.Popen(
                            self.argv(target), cwd=self.root, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE))
                    results = []
                    for process in processes:
                        out, err = process.communicate(timeout=30)
                        results.append((process.returncode, out, err))
                finally:
                    for process in processes:
                        if process.poll() is None:
                            process.kill()
                            process.communicate()
                self.assertEqual([0, 2], sorted(code for code, _, _ in results), results)
                for code, out, err in results:
                    if code == 2:
                        self.assertEqual("", out)
                        self.assertIn("must not already exist", err)
                        self.assertNotIn("Traceback", err)
                    else:
                        self.assertEqual(GOLDEN_SEED7["small"]["summary"], json.loads(out))
                        self.assertEqual("", err)
                self.assertEqual(GOLDEN_SEED7["small"]["tree"], tree_digest(target))

    def test_collision_at_actual_mkdir_preserves_arriving_owner(self):
        target = self.root / "late-arrival"
        original = Path.mkdir
        observed = []

        def create_first(path, *args, **kwargs):
            if path == target and not observed:
                observed.append((args, kwargs))
                original(target)
                (target / "caller-note").write_bytes(b"SYNTHETIC: retain late owner")
            return original(path, *args, **kwargs)

        with patch.object(Path, "mkdir", create_first):
            with self.assertRaises(FileExistsError):
                gen.generate(target, TINY, seed=7)
        self.assertEqual(1, len(observed), "the actual reservation was not observed")
        self.assertEqual(["caller-note"], sorted(p.name for p in target.iterdir()))
        self.assertEqual(b"SYNTHETIC: retain late owner", (target / "caller-note").read_bytes())

    def test_refusal_preserves_existing_empty_directory_metadata(self):
        target = self.root / "existing"
        target.mkdir()
        before = target.stat()
        with self.assertRaises(FileExistsError):
            gen.generate(target, TINY, seed=7)
        after = target.stat()
        self.assertEqual((before.st_ino, before.st_mode, before.st_mtime_ns),
                         (after.st_ino, after.st_mode, after.st_mtime_ns))
        self.assertEqual([], list(target.iterdir()))

    def test_partial_new_output_is_retained_and_cannot_be_reused(self):
        marker = self.root / "caller-note"
        marker.write_bytes(b"SYNTHETIC: keep unrelated data")
        target = self.root / "new-output"
        original = Path.write_text
        observed = []

        def fail_second_report(path, *args, **kwargs):
            if path == target / "final-report.md":
                observed.append(path)
                raise OSError("synthetic write interruption")
            return original(path, *args, **kwargs)

        with patch.object(Path, "write_text", fail_second_report):
            with self.assertRaisesRegex(OSError, "synthetic write interruption"):
                gen.generate(target, TINY, seed=7)
        self.assertEqual(1, len(observed))
        self.assertTrue((target / "executive-summary.md").is_file())
        self.assertFalse((target / "manifest.json").exists())
        partial = tree_digest(target)
        with self.assertRaises(FileExistsError):
            gen.generate(target, TINY, seed=7)
        self.assertEqual(partial, tree_digest(target))
        self.assertEqual(b"SYNTHETIC: keep unrelated data", marker.read_bytes())


if __name__ == "__main__":
    unittest.main()
