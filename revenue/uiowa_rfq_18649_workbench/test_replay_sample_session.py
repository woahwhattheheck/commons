"""Create-only output and observed-result handling for the browser replay runner."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import replay_sample_session as replay


class ReplayRunnerTests(unittest.TestCase):
    def result(self, **changes):
        result = {"run": 18, "failures": 0, "errors": 0, "skipped": 0,
                  "expected_failures": 0, "unexpected_successes": 0, "optimization": 0}
        result.update(changes)
        return result

    def output(self, result):
        return replay.RESULT_MARKER + json.dumps(result)

    def test_valid_observed_counts_are_returned_not_replaced_with_constant(self):
        record = self.result(run=23)
        self.assertEqual(replay.checked_result(self.output(record), 0, 0), record)

    def test_nonzero_child_exit_rejects_even_successful_looking_result(self):
        with self.assertRaises(RuntimeError):
            replay.checked_result(self.output(self.result()), 1, 0)

    def test_missing_or_multiple_result_lines_rejected(self):
        for text in ("", "OK", self.output(self.result()) + "\n" + self.output(self.result())):
            with self.subTest(text=text), self.assertRaises(RuntimeError):
                replay.checked_result(text, 0, 0)

    def test_empty_failed_skipped_and_expected_failure_suites_rejected(self):
        for changes in ({"run": 0}, {"failures": 1}, {"errors": 1}, {"skipped": 1},
                        {"expected_failures": 1}, {"unexpected_successes": 1}):
            with self.subTest(changes=changes), self.assertRaises(RuntimeError):
                replay.checked_result(self.output(self.result(**changes)), 0, 0)

    def test_invalid_counts_and_wrong_optimization_rejected(self):
        for changes in ({"run": True}, {"run": "18"}, {"run": -1}, {"optimization": 1}):
            with self.subTest(changes=changes), self.assertRaises(RuntimeError):
                replay.checked_result(self.output(self.result(**changes)), 0, 0)

    def test_incomplete_or_extra_fields_rejected(self):
        for record in ({"run": 18}, [], self.result(extra=1)):
            with self.subTest(record=record), self.assertRaises(RuntimeError):
                replay.checked_result(self.output(record), 0, 0)

    def test_existing_directory_is_unchanged_and_never_runs_browser(self):
        with tempfile.TemporaryDirectory() as temp:
            existing = Path(temp) / "existing"
            existing.mkdir()
            marker = existing / "user-work.json"
            marker.write_bytes(b"preserve exactly\n")
            with patch.object(replay, "run_tests") as run, self.assertRaises(FileExistsError):
                replay.replay(existing)
            run.assert_not_called()
            self.assertEqual(marker.read_bytes(), b"preserve exactly\n")
            self.assertEqual(sorted(path.name for path in existing.iterdir()), ["user-work.json"])

    def test_file_and_symlink_output_paths_are_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "target"
            target.write_bytes(b"existing user file")
            directory = root / "directory"
            directory.mkdir()
            link = root / "directory-link"
            link.symlink_to(directory, target_is_directory=True)
            broken = root / "broken-link"
            broken.symlink_to(root / "absent")
            for path in (target, link, broken):
                with self.subTest(path=path), self.assertRaises(FileExistsError):
                    replay.make_output(path)
            self.assertEqual(target.read_bytes(), b"existing user file")
            self.assertEqual(list(directory.iterdir()), [])
            self.assertFalse((root / "absent").exists())

    def test_missing_parent_not_recursively_created(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp) / "absent"
            with self.assertRaises(FileNotFoundError):
                replay.make_output(parent / "output")
            self.assertFalse(parent.exists())

    def test_existing_output_file_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "result.json"
            replay.write_new(target, b"original")
            with self.assertRaises(FileExistsError):
                replay.write_new(target, b"replacement")
            self.assertEqual(target.read_bytes(), b"original")

    def test_test_failure_writes_failure_not_pass_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "run"
            with patch.object(replay, "run_tests", side_effect=RuntimeError("observed failure")), \
                    patch.object(replay, "capture") as capture, self.assertRaises(RuntimeError):
                replay.replay(out)
            capture.assert_not_called()
            self.assertFalse((out / "run_receipt.json").exists())
            self.assertEqual(json.loads((out / "failure.json").read_text())["result"], "FAIL")

    def test_source_drift_prevents_success_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "run"
            expected = {"bytes": 1, "sha256": "a", "git_blob_sha1": "b"}
            drifted = {"bytes": 2, "sha256": "c", "git_blob_sha1": "d"}
            sequence = [expected] * len(replay.ASSETS) + [drifted] * len(replay.ASSETS)
            with patch.object(replay, "digest", side_effect=sequence), \
                    patch.object(replay, "run_tests", side_effect=[self.result(), self.result(optimization=1)]), \
                    patch.object(replay, "capture", return_value={}), self.assertRaises(RuntimeError):
                replay.replay(out)
            self.assertFalse((out / "run_receipt.json").exists())
            self.assertIn("Source changed", json.loads((out / "failure.json").read_text())["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
