#!/usr/bin/env python3
"""Interrupted result streams must retain only delimiter-complete records."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from host import battery_report as report

ROOT = Path(__file__).resolve().parent
SHA = "a" * 40


def stream(*records: tuple[str, str, str | int]) -> bytes:
    return b"".join(str(field).encode("utf-8") + b"\0" for record in records for field in record)


class ParseTruncationTests(unittest.TestCase):
    def test_unterminated_exit_is_not_a_completed_python_result(self):
        prefix = stream(("checkout_sha", SHA, ""), ("python3", "test_done.py", 0))
        _, rows, complete, problems = report.parse_results(prefix + b"python3\0test_cut.py\0" + b"12")
        self.assertFalse(complete)
        self.assertEqual([row["path"] for row in rows], ["test_done.py"])
        self.assertIn("unterminated result stream", problems)
        self.assertIn("partial result record", problems)

    def test_unterminated_zero_does_not_create_a_pass(self):
        raw = stream(("checkout_sha", SHA, "")) + b"node\0test_cut.js\0" + b"0"
        _, rows, complete, problems = report.parse_results(raw)
        self.assertFalse(complete)
        self.assertEqual(rows, [])
        self.assertIn("partial result record", problems)

    def test_unterminated_completion_code_is_not_a_completion_marker(self):
        prefix = stream(("checkout_sha", SHA, ""), ("node", "test_done.js", 0))
        _, rows, complete, problems = report.parse_results(prefix + b"battery_complete\0\0" + b"0")
        self.assertFalse(complete)
        self.assertEqual(len(rows), 1)
        self.assertIn("completion marker is missing", problems)
        self.assertIn("partial result record", problems)

    def test_every_cut_retains_exactly_the_terminated_test_records(self):
        # Inspect every byte boundary, including inside a multibyte path and
        # each digit of a three-digit exit. No truncated prefix is a result.
        records = [
            ("checkout_sha", SHA, ""),
            ("python3", "./test_ok.py", 0),
            ("node", "test_雪.js", 123),
            ("python3", "test_last.py", 255),
            ("battery_complete", "", 1),
        ]
        encoded = [stream(record) for record in records]
        raw = b"".join(encoded)
        ends = []
        total = 0
        for item in encoded:
            total += len(item)
            ends.append(total)
        for cut in range(len(raw) + 1):
            with self.subTest(cut=cut):
                _, rows, complete, _ = report.parse_results(raw[:cut])
                expected = [
                    (record[1].removeprefix("./"), record[2])
                    for record, end in zip(records, ends)
                    if record[0] in ("python3", "node") and end <= cut
                ]
                self.assertEqual([(row["path"], row["exit_code"]) for row in rows], expected)
                self.assertEqual(complete, cut == len(raw))

    def test_all_exit_codes_require_the_final_delimiter(self):
        prefix = stream(("checkout_sha", SHA, ""))
        errors = []
        for command, path in (("python3", "test.py"), ("node", "test.js")):
            for code in range(256):
                record = stream((command, path, code))
                _, rows, complete, _ = report.parse_results(prefix + record[:-1])
                if rows or complete:
                    errors.append((command, code))
        self.assertEqual(errors, [], f"{len(errors)} unterminated exits became completed records")

    def test_a_fully_written_failure_survives_the_partial_next_result(self):
        prefix = stream(("checkout_sha", SHA, ""), ("python3", "test_failed.py", 7))
        _, rows, complete, problems = report.parse_results(prefix + b"node\0test_cut.js\0" + b"0")
        self.assertFalse(complete)
        self.assertEqual([(row["path"], row["exit_code"]) for row in rows], [("test_failed.py", 7)])
        self.assertIn("unterminated result stream", problems)

    def test_complete_streams_are_unchanged(self):
        for code in (0, 1, 12, 123, 255):
            with self.subTest(code=code):
                raw = stream(("checkout_sha", SHA, ""), ("python3", "./test.py", code),
                             ("battery_complete", "", int(code != 0)))
                sha, rows, complete, problems = report.parse_results(raw)
                self.assertEqual(sha, SHA)
                self.assertTrue(complete)
                self.assertEqual(problems, [])
                self.assertEqual(rows, [{"path": "test.py", "command": ["python3", "./test.py"], "exit_code": code}])

    def test_partial_command_and_path_keep_prior_results(self):
        prefix = stream(("checkout_sha", SHA, ""), ("node", "test_done.js", 0))
        for suffix in (b"p", b"python3", b"python3\0", b"python3\0test", b"python3\0test.py\0"):
            with self.subTest(suffix=suffix):
                _, rows, complete, _ = report.parse_results(prefix + suffix)
                self.assertFalse(complete)
                self.assertEqual([row["path"] for row in rows], ["test_done.js"])


class CliTruncationTests(unittest.TestCase):
    def test_real_git_cli_and_summary_exclude_a_partial_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args: str) -> str:
                return subprocess.run(["git", "-C", str(root), *args], check=True,
                                      capture_output=True, text=True).stdout.strip()
            git("init", "-q")
            git("config", "user.name", "Battery Truncation Test")
            git("config", "user.email", "battery-test@example.invalid")
            for name in ("test_finished.py", "test_cut.py"):
                (root / name).write_text("pass\n", encoding="utf-8")
            git("add", ".")
            git("-c", "commit.gpgsign=false", "commit", "-qm", "fixture")
            sha = git("rev-parse", "HEAD")
            raw = stream(("checkout_sha", sha, ""), ("python3", "test_finished.py", 0))
            raw += b"python3\0test_cut.py\0" + b"12"
            inputs, output, summary = root / "results.nul", root / "report.json", root / "summary.md"
            inputs.write_bytes(raw)
            process = subprocess.run(
                [sys.executable, str(ROOT / "host/battery_report.py"), "--root", str(root),
                 "--results", str(inputs), "--output", str(output), "--summary", str(summary),
                 "--outcome", "cancelled"], capture_output=True, text=True, check=True,
            )
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(process.returncode, 0)
            self.assertEqual(data["conclusion"], "INCOMPLETE")
            self.assertFalse(data["complete"])
            self.assertEqual(data["counts"], {"completed_files": 1, "passed_files": 1,
                                             "failed_files": 0, "unresolved_source_files": 0})
            self.assertEqual(data["results"][0]["source_blob_sha"], git("rev-parse", sha + ":test_finished.py"))
            note = summary.read_text(encoding="utf-8")
            self.assertIn("1 completed files, 0 failed files", note)
            self.assertNotIn("test_cut.py", note)
            self.assertEqual(inputs.read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
