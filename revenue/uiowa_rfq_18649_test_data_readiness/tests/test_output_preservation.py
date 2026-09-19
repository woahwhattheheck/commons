"""Source-bound, fictional-only CLI output preservation regressions for #16408.

UIOWA047_ASSESSOR may select an immutable source reconstruction for review.
Both library and CLI tests execute the same captured source buffer. No network,
repository fixture mutation, second assessor, or expected-output regeneration.
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

SOURCE = Path(os.environ.get("UIOWA047_ASSESSOR", str(Path(__file__).resolve().parents[1] / "test_data_assessor.py")))
SOURCE_BYTES = SOURCE.read_bytes()
SOURCE_BLOB = hashlib.sha1(b"blob " + str(len(SOURCE_BYTES)).encode() + b"\0" + SOURCE_BYTES).hexdigest()
FIXTURE = {
    "label": "FICTIONAL output-preservation rehearsal; not University findings",
    "as_of": "2026-09-19",
    "datasets": [{"dataset_id": "SYN-OUTPUT", "service": "ESS", "data_origin": "synthetic",
                  "required_boundary_cases": ["empty", "unicode-\u00e9"], "covered_boundary_cases": [],
                  "last_refreshed": "2026-09-20", "refresh_cadence_days": 30,
                  "cleanup_required": True, "cleanup_last_verified": "2026-09-20"}],
}


class OutputPreservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "test_data_assessor.py"
        self.source.write_bytes(SOURCE_BYTES)
        self.catalog = self.root / "catalog.json"
        self.input_bytes = (json.dumps(FIXTURE, ensure_ascii=True, sort_keys=True) + "\n").encode()
        self.catalog.write_bytes(self.input_bytes)
        self.output = self.root / "report.json"
        self.module = types.ModuleType("uiowa047_output_preservation_subject")
        self.module.__file__ = str(self.source)
        exec(compile(SOURCE_BYTES, str(self.source), "exec"), self.module.__dict__)

    def cli(self, output=None, fmt="json", catalog=None):
        mode = [] if not sys.flags.optimize else ["-" + "O" * sys.flags.optimize]
        argv = [sys.executable, *mode, "-B", str(self.source), str(catalog or self.catalog), "--format", fmt]
        if output is not None:
            argv += ["--output", str(output)]
        return subprocess.run(argv, capture_output=True, timeout=10)

    def preserved(self):
        self.assertEqual(self.catalog.read_bytes(), self.input_bytes)
        self.assertEqual(self.source.read_bytes(), SOURCE_BYTES)
        self.assertEqual(list(self.root.glob(".uiowa047-*.tmp")), [])

    def refused(self, output, fmt="json", catalog=None):
        result = self.cli(output, fmt, catalog)
        self.assertEqual(result.returncode, 2, result.stderr.decode(errors="replace"))
        self.assertEqual(result.stdout, b"")
        self.assertNotIn(b"Traceback", result.stderr)
        self.assertIn(b"cannot write report:", result.stderr)
        self.preserved()
        return result

    def test_same_path_refuses_without_source_loss(self):
        self.refused(self.catalog)

    def test_resolved_parent_alias_refuses(self):
        sub = self.root / "child"
        sub.mkdir()
        self.refused(sub / ".." / "catalog.json")

    def test_output_symlink_to_catalog_refuses(self):
        self.output.symlink_to(self.catalog)
        self.refused(self.output)
        self.assertTrue(self.output.is_symlink())

    def test_output_hardlink_to_catalog_refuses(self):
        os.link(self.catalog, self.output)
        self.refused(self.output)
        self.assertTrue(self.catalog.samefile(self.output))

    def test_input_symlink_and_real_output_alias_refuse(self):
        alias = self.root / "input-link.json"
        alias.symlink_to(self.catalog)
        self.refused(self.catalog, catalog=alias)

    def test_parent_symlink_alias_refuses(self):
        alias = self.root / "parent-link"
        alias.symlink_to(self.root, target_is_directory=True)
        self.refused(alias / "catalog.json")

    def test_distinct_output_symlink_refuses_without_touching_target(self):
        target = self.root / "previous.json"
        target.write_bytes(b"retained previous report\n")
        self.output.symlink_to(target)
        self.refused(self.output)
        self.assertEqual(target.read_bytes(), b"retained previous report\n")
        self.assertTrue(self.output.is_symlink())

    def test_dangling_output_symlink_refuses(self):
        target = self.root / "absent.json"
        self.output.symlink_to(target)
        self.refused(self.output)
        self.assertFalse(target.exists())
        self.assertTrue(self.output.is_symlink())

    def test_missing_parent_is_clean_error(self):
        self.refused(self.root / "absent" / "report.json")
        self.assertFalse((self.root / "absent").exists())

    def test_directory_destination_is_clean_error(self):
        self.output.mkdir()
        sentinel = self.output / "keep.txt"
        sentinel.write_bytes(b"keep")
        self.refused(self.output)
        self.assertEqual(sentinel.read_bytes(), b"keep")

    def test_new_json_output_equals_stdout_and_preserves_input(self):
        expected = self.cli()
        result = self.cli(self.output)
        self.assertEqual(expected.returncode, 0, expected.stderr)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(self.output.read_bytes(), expected.stdout)
        report = json.loads(expected.stdout)
        self.assertEqual(report["dataset_count"], 1)
        states = {c["check_id"]: c["state"] for c in report["datasets"][0]["checks"]}
        self.assertEqual(states["refresh_freshness"], "UNKNOWN")
        self.assertEqual(states["cleanup"], "UNKNOWN")
        self.assertEqual(states["representativeness"], "OBSERVED_GAP")
        self.preserved()

    def test_new_markdown_output_equals_stdout(self):
        expected = self.cli(fmt="markdown")
        result = self.cli(self.output, fmt="markdown")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.output.read_bytes(), expected.stdout)
        self.assertIn(b"UNKNOWN", expected.stdout)
        self.preserved()

    def test_existing_distinct_report_replacement_remains_supported(self):
        self.output.write_bytes(b"previous report\n")
        self.output.chmod(0o640)
        expected = self.cli().stdout
        for _ in range(2):
            result = self.cli(self.output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.output.read_bytes(), expected)
            self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o640)
            self.preserved()

    def test_distinct_hardlink_report_does_not_rewrite_other_link(self):
        target = self.root / "previous.json"
        target.write_bytes(b"other name retains its bytes\n")
        os.link(target, self.output)
        result = self.cli(self.output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(target.read_bytes(), b"other name retains its bytes\n")
        self.assertFalse(target.samefile(self.output))
        self.preserved()

    def test_malformed_input_does_not_mutate_existing_report(self):
        self.catalog.write_bytes(b"not json\n")
        self.input_bytes = self.catalog.read_bytes()
        self.output.write_bytes(b"keep\n")
        result = self.cli(self.output)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")
        self.assertNotIn(b"Traceback", result.stderr)
        self.assertEqual(self.output.read_bytes(), b"keep\n")
        self.preserved()

    def test_unencodable_markdown_does_not_truncate_previous_report(self):
        payload = copy.deepcopy(FIXTURE)
        payload["datasets"][0]["owner_role"] = "\ud800"
        self.input_bytes = (json.dumps(payload) + "\n").encode()
        self.catalog.write_bytes(self.input_bytes)
        self.output.write_bytes(b"retain before Unicode error\n")
        self.refused(self.output, fmt="markdown")
        self.assertEqual(self.output.read_bytes(), b"retain before Unicode error\n")

    def fault(self, operation, side_effect, existing=True):
        if existing:
            self.output.write_bytes(b"previous complete report\n")
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch(operation, side_effect=side_effect), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as error:
                self.module.main([str(self.catalog), "--format", "json", "--output", str(self.output)])
        self.assertEqual(error.exception.code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("cannot write report:", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())
        if existing:
            self.assertEqual(self.output.read_bytes(), b"previous complete report\n")
        else:
            self.assertFalse(self.output.exists())
        self.preserved()

    def test_flush_to_disk_failure_preserves_previous_report(self):
        self.fault("os.fsync", OSError("injected fsync failure"))

    def test_replacement_failure_preserves_previous_report(self):
        self.fault("os.replace", PermissionError("injected replace refusal"))

    def test_replacement_failure_leaves_new_output_absent(self):
        self.fault("os.replace", PermissionError("injected replace refusal"), existing=False)

    def test_staging_creation_failure_preserves_previous_report(self):
        self.fault("tempfile.mkstemp", PermissionError("injected staging refusal"))

    def test_descriptor_wrap_failure_closes_descriptor_and_cleans_staging(self):
        observed = []
        original_close = os.close
        def close(fd):
            observed.append(fd)
            return original_close(fd)
        with patch("os.close", side_effect=close):
            self.fault("os.fdopen", OSError("injected descriptor wrapping failure"))
        self.assertGreaterEqual(len(observed), 1)

    def test_mode_copy_failure_preserves_previous_report(self):
        self.fault("os.chmod", PermissionError("injected mode-copy refusal"))

    def test_partial_staging_write_failure_preserves_previous_report(self):
        original_fdopen = os.fdopen
        class PartialWriter:
            def __init__(self, *args, **kwargs):
                self.inner = original_fdopen(*args, **kwargs)
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.inner.close()
            def write(self, text):
                self.inner.write(text[:11])
                self.inner.flush()
                raise OSError("injected failure after partial staging write")
        self.fault("os.fdopen", PartialWriter)

    def test_signal_interrupt_cleans_staging_and_preserves_prior_bytes(self):
        self.output.write_bytes(b"keep after interrupt\n")
        with patch("os.fsync", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.module.main([str(self.catalog), "--output", str(self.output)])
        self.assertEqual(self.output.read_bytes(), b"keep after interrupt\n")
        self.preserved()

    def test_alias_introduced_during_staging_is_rechecked(self):
        original_fsync = os.fsync
        def change_destination(fd):
            original_fsync(fd)
            os.link(self.catalog, self.output)
        stderr = io.StringIO()
        with patch("os.fsync", side_effect=change_destination), contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as error:
                self.module.main([str(self.catalog), "--format", "json", "--output", str(self.output)])
        self.assertEqual(error.exception.code, 2)
        self.assertIn("must not alias the source catalog", stderr.getvalue())
        self.assertTrue(self.catalog.samefile(self.output))
        self.preserved()

    def test_stream_flush_failure_preserves_previous_report(self):
        original_fdopen = os.fdopen
        class FlushFailure:
            def __init__(self, *args, **kwargs):
                self.inner = original_fdopen(*args, **kwargs)
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.inner.close()
            def write(self, text):
                return self.inner.write(text)
            def flush(self):
                raise OSError("injected stream flush failure")
        self.fault("os.fdopen", FlushFailure)


if __name__ == "__main__":
    print("SOURCE_BLOB=" + SOURCE_BLOB, flush=True)
    unittest.main(verbosity=2)
