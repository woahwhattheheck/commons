"""Regression for UIOWA-095's former destructive --out behavior.

All executable cases use this test's own temporary directory. These checks
exercise the actual generator and CLI; they do not replace generation with a
stub or claim to test the complete benchmark/workflow implementation.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import generate_collection as gen


TINY = gen.Profile("safety-fixture", evidence=12, findings=6,
                   recommendations=4, statements=6, documents=4,
                   doc_body_lines=2, big_doc_every=2, big_doc_body_lines=4)


def snapshot(root: Path) -> dict[str, tuple[str, str]]:
    """Include directories and raw file bytes; never follow fixture symlinks."""
    result = {}
    for path in sorted(root.rglob("*")):
        name = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[name] = ("symlink", str(path.readlink()))
        elif path.is_dir():
            result[name] = ("directory", "")
        else:
            result[name] = ("file", hashlib.sha256(path.read_bytes()).hexdigest())
    return result


class GeneratorOutputSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="uiowa095-safe-output-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def evidence_tree(self) -> Path:
        target = self.root / "existing-evidence"
        (target / "nested").mkdir(parents=True)
        (target / "nested" / "operator-note.txt").write_bytes(b"SYNTHETIC sentinel\x00\xff\n")
        # A manifest claiming synthetic provenance never grants deletion rights.
        (target / "manifest.json").write_text(json.dumps({"synthetic": True,
            "schema": "uiowa-095-collection-v1", "operator_note": "KEEP"}), encoding="utf-8")
        return target

    def test_existing_evidence_tree_is_refused_without_changing_any_bytes(self):
        target = self.evidence_tree()
        before = snapshot(self.root)
        with self.assertRaises(FileExistsError):
            gen.generate(target, TINY)
        self.assertEqual(snapshot(self.root), before)

    def test_empty_existing_directory_is_also_refused(self):
        target = self.root / "empty"
        target.mkdir()
        with self.assertRaises(FileExistsError):
            gen.generate(target, TINY)
        self.assertEqual(list(target.iterdir()), [])

    def test_existing_regular_file_is_untouched(self):
        target = self.root / "evidence.txt"
        target.write_bytes(b"SYNTHETIC: retain exactly\x00\xfe")
        before = target.read_bytes()
        with self.assertRaises(FileExistsError):
            gen.generate(target, TINY)
        self.assertEqual(target.read_bytes(), before)

    def test_symlink_to_existing_evidence_is_refused_and_target_untouched(self):
        target = self.evidence_tree()
        link = self.root / "selected-output"
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")
        before = snapshot(self.root)
        with self.assertRaises(FileExistsError):
            gen.generate(link, TINY)
        self.assertEqual(snapshot(self.root), before)

    def test_dangling_symlink_does_not_create_its_target(self):
        target = self.root / "never-create"
        link = self.root / "dangling"
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")
        with self.assertRaises(FileExistsError):
            gen.generate(link, TINY)
        self.assertTrue(link.is_symlink())
        self.assertFalse(target.exists())

    def test_previously_generated_collection_is_not_implicitly_disposable(self):
        target = self.root / "collection"
        gen.generate(target, TINY, seed=7)
        (target / "retained-review.txt").write_text("SYNTHETIC: operator added this", encoding="utf-8")
        before = snapshot(self.root)
        with self.assertRaises(FileExistsError):
            gen.generate(target, TINY, seed=8)
        self.assertEqual(snapshot(self.root), before)

    def test_existing_documents_child_does_not_grant_overwrite_permission(self):
        target = self.root / "collection"
        (target / "documents").mkdir(parents=True)
        (target / "documents" / "D-001.md").write_text("SYNTHETIC: retained original", encoding="utf-8")
        before = snapshot(self.root)
        with self.assertRaises(FileExistsError):
            gen.generate(target, TINY)
        self.assertEqual(snapshot(self.root), before)

    def test_current_working_directory_cannot_be_selected_as_output(self):
        target = self.evidence_tree()
        before = snapshot(self.root)
        result = subprocess.run([sys.executable, str(Path(gen.__file__).resolve()),
                                 "--out", ".", "--profile", "small"], cwd=target,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(snapshot(self.root), before)
        self.assertEqual(result.stdout, "")

    def test_cli_refusal_has_no_success_payload_or_traceback(self):
        target = self.evidence_tree()
        before = snapshot(self.root)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as raised:
                gen.main(["--out", str(target), "--profile", "small"])
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("must not already exist", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())
        self.assertEqual(snapshot(self.root), before)

    def test_new_nested_destination_generates_complete_collection(self):
        target = self.root / "new-parent" / "new-collection"
        result = gen.generate(target, TINY, seed=7)
        expected = {"documents", "evidence.csv", "findings.csv", "recommendations.csv",
                    "trace-map.csv", "manifest.json", "final-report.md", "executive-summary.md"}
        self.assertEqual({p.name for p in target.iterdir()}, expected)
        self.assertEqual(result["evidence_rows"], 12)
        self.assertEqual(result["trace_rows"], 6)
        self.assertEqual(result["documents_on_disk"], 3)
        manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        self.assertIs(manifest["synthetic"], True)
        self.assertEqual(manifest["seed"], 7)

    def test_fresh_same_seed_generations_are_byte_identical(self):
        a, b = self.root / "a", self.root / "b"
        first = gen.generate(a, TINY, seed=7)
        second = gen.generate(b, TINY, seed=7)
        self.assertEqual(first, second)
        self.assertEqual(snapshot(a), snapshot(b))

    def test_fresh_sibling_generation_preserves_prior_run_and_unrelated_tree(self):
        original = self.evidence_tree()
        prior = self.root / "prior"
        gen.generate(prior, TINY, seed=7)
        evidence_before, prior_before = snapshot(original), snapshot(prior)
        gen.generate(self.root / "fresh", TINY, seed=8)
        self.assertEqual(snapshot(original), evidence_before)
        self.assertEqual(snapshot(prior), prior_before)

    def test_cli_fresh_destination_succeeds(self):
        target = self.root / "fresh-cli"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(gen.main(["--out", str(target), "--profile", "small"]), 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["evidence_rows"], 200)
        self.assertTrue((target / "manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
