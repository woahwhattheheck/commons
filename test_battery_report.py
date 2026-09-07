#!/usr/bin/env python3
"""Offline battery reporting tests, including the real workflow's Bash loop."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from host import battery_report as report

ROOT = Path(__file__).resolve().parent


def stream(*records):
    return b"".join(str(field).encode("utf-8") + b"\0" for record in records for field in record)


def battery_script():
    text = (ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")
    block = text.split("      - name: the whole battery, one failure fails the run\n", 1)[1]
    block = block.split("        run: |\n", 1)[1]
    lines = []
    for line in block.splitlines():
        if line and not line.startswith("          "):
            break
        lines.append(line[10:] if line else "")
    return "\n".join(lines) + "\n"


class BatteryReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Battery Test")
        self.git("config", "user.email", "battery-test@example.invalid")
        (self.root / "infra").mkdir()
        self.files = {"test_alpha.py": "print('alpha')\n", "infra/test_beta.py": "raise SystemExit(7)\n"}
        for name, content in self.files.items():
            (self.root / name).write_text(content, encoding="utf-8")
        self.commit()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True, text=True).stdout.strip()

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        self.sha = self.git("rev-parse", "HEAD")

    def raw(self, *records, failed=0):
        return stream(("checkout_sha", self.sha, ""), *records, ("battery_complete", "", failed))

    def build(self, raw, outcome="success", environ=None):
        return report.build_report(self.root, raw, outcome, environ or {})

    def test_success_is_linked_to_the_recorded_commit(self):
        data = self.build(self.raw(("python3", "./test_alpha.py", 0)), environ={"GITHUB_SHA": "b" * 40, "GITHUB_RUN_ID": "123", "GITHUB_WORKFLOW_REF": "owner/repo/.github/workflows/tests.yml@refs/heads/main"})
        self.assertEqual(data["conclusion"], "PASSED")
        self.assertEqual(data["checkout_sha"], self.sha)
        self.assertEqual(data["event_sha"], "b" * 40)
        self.assertEqual(data["run_id"], "123")
        self.assertEqual(data["workflow_ref"], "owner/repo/.github/workflows/tests.yml@refs/heads/main")
        self.assertEqual(data["results"][0]["source_blob_sha"], self.git("rev-parse", self.sha + ":test_alpha.py"))

    def test_moving_head_does_not_change_source_attribution(self):
        raw = self.raw(("python3", "test_alpha.py", 0))
        old_sha = self.sha
        old_blob = self.git("rev-parse", old_sha + ":test_alpha.py")
        (self.root / "test_alpha.py").write_text("print('changed')\n", encoding="utf-8")
        self.commit()
        data = self.build(raw)
        self.assertNotEqual(old_sha, self.sha)
        self.assertEqual(data["checkout_sha"], old_sha)
        self.assertEqual(data["results"][0]["source_blob_sha"], old_blob)

    def test_untracked_path_is_not_invented_as_a_source(self):
        data = self.build(self.raw(("python3", "test_not_tracked.py", 9), failed=1), "failure")
        self.assertEqual(data["conclusion"], "FAILED")
        self.assertIsNone(data["results"][0]["source_blob_sha"])
        self.assertFalse(data["results"][0]["source_in_checkout_commit"])
        self.assertEqual(data["counts"]["unresolved_source_files"], 1)

    def test_interrupted_and_truncated_records_keep_completed_files(self):
        prefix = stream(("checkout_sha", self.sha, ""), ("python3", "test_alpha.py", 0))
        for raw in (prefix, prefix + b"python3\0infra/test_beta.py\0", prefix + b"python3\0partial"):
            with self.subTest(raw=raw):
                data = self.build(raw, "cancelled")
                self.assertEqual(data["conclusion"], "INCOMPLETE")
                self.assertFalse(data["complete"])
                self.assertEqual(data["counts"]["completed_files"], 1)

    def test_missing_empty_unknown_commit_and_zero_tests_are_not_passes(self):
        for raw in (None, b"", stream(("checkout_sha", "f" * 40, ""), ("battery_complete", "", 0))):
            with self.subTest(raw=raw):
                self.assertEqual(self.build(raw)["conclusion"], "INCOMPLETE")
        self.assertEqual(self.build(self.raw())["conclusion"], "NO_TESTS")
        self.assertEqual(self.build(self.raw(("python3", "test_alpha.py", 0)), "failure")["conclusion"], "HARNESS_FAILED")

    def test_malformed_records_do_not_become_passing_evidence(self):
        bad = [
            ("python3", "test_alpha.py", "no"),
            ("python3", "test_alpha.py", 256),
            ("python3", "test_alpha.py", "9" * 5000),
            ("python3", "../test_alpha.py", 0),
            ("python3", "/test_alpha.py", 0),
            ("other", "test_alpha.py", 0),
            ("checkout_sha", self.sha, ""),
        ]
        for record in bad:
            with self.subTest(record=record):
                self.assertEqual(self.build(self.raw(record))["conclusion"], "INCOMPLETE")
        after = self.raw() + stream(("python3", "test_alpha.py", 0))
        self.assertEqual(self.build(after)["conclusion"], "INCOMPLETE")
        mismatch = self.raw(("python3", "test_alpha.py", 7), failed=0)
        self.assertEqual(self.build(mismatch, "failure")["conclusion"], "INCOMPLETE")
        self.assertEqual(self.build(self.raw(("python3", "test_alpha.py", 7), failed=1))["conclusion"], "INCOMPLETE")

    def test_unusual_filename_and_summary_are_lossless_and_escaped(self):
        name = "test_a | <b>`\n\t.py"
        (self.root / name).write_text("pass\n", encoding="utf-8")
        self.commit()
        data = self.build(self.raw(("python3", "./" + name, 3), failed=1), "failure")
        self.assertEqual(data["results"][0]["path"], name)
        self.assertTrue(data["results"][0]["source_in_checkout_commit"])
        markdown = report.summary(data)
        self.assertIn("&lt;b&gt;", markdown)
        self.assertIn("&#124;", markdown)
        self.assertIn("\\n\\t.py", markdown)
        self.assertNotIn("<b>", markdown)

    def test_cli_writes_json_and_appends_summary_without_exporting_secrets(self):
        result_path = self.root / "results.nul"
        result_path.write_bytes(self.raw(("python3", "infra/test_beta.py", 7), failed=1))
        output = self.root / "report.json"
        note = self.root / "summary.md"
        note.write_text("Earlier step\n", encoding="utf-8")
        env = dict(os.environ, DO_NOT_EXPORT_SECRET="private-test-value", GITHUB_JOB="battery")
        process = subprocess.run(
            [sys.executable, str(ROOT / "host/battery_report.py"), "--root", str(self.root), "--results", str(result_path),
             "--output", str(output), "--summary", str(note), "--outcome", "failure"],
            check=True, capture_output=True, text=True, env=env,
        )
        text = output.read_text(encoding="utf-8")
        self.assertEqual(json.loads(text)["conclusion"], "FAILED")
        self.assertEqual(json.loads(text)["job_name"], "battery")
        self.assertTrue(note.read_text(encoding="utf-8").startswith("Earlier step\n"))
        self.assertNotIn("private-test-value", text + note.read_text(encoding="utf-8") + process.stdout + process.stderr)

    @unittest.skipUnless(shutil.which("bash") and shutil.which("node"), "workflow requires Bash and Node")
    def test_real_workflow_loop_records_exits_and_continues_after_failures(self):
        (self.root / "test_omega.py").write_text("print('after earlier failure')\n", encoding="utf-8")
        (self.root / "test_node_pass.js").write_text("process.exit(0);\n", encoding="utf-8")
        (self.root / "test_node_fail.js").write_text("process.exit(4);\n", encoding="utf-8")
        self.commit()
        env = dict(os.environ, RUNNER_TEMP=str(self.root))
        process = subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", battery_script()],
                                 cwd=self.root, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(process.returncode, 1)
        path = self.root / "commons-battery-results.nul"
        self.assertTrue(path.is_file(), "workflow emitted no structured result stream")
        data = self.build(path.read_bytes(), "failure")
        self.assertTrue(data["complete"])
        self.assertEqual(data["conclusion"], "FAILED")
        self.assertEqual(data["counts"], {"completed_files": 5, "passed_files": 3, "failed_files": 2, "unresolved_source_files": 0})
        codes = {row["path"]: row["exit_code"] for row in data["results"]}
        self.assertEqual(codes["infra/test_beta.py"], 7)
        self.assertEqual(codes["test_node_fail.js"], 4)
        self.assertEqual(codes["test_omega.py"], 0)

    @unittest.skipUnless(shutil.which("bash") and shutil.which("node"), "workflow requires Bash and Node")
    def test_real_workflow_success_and_empty_discovery(self):
        (self.root / "infra/test_beta.py").write_text("pass\n", encoding="utf-8")
        self.commit()
        env = dict(os.environ, RUNNER_TEMP=str(self.root))
        for expected_count, conclusion in ((2, "PASSED"), (0, "NO_TESTS")):
            with self.subTest(completed_files=expected_count):
                process = subprocess.run(
                    ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", battery_script()],
                    cwd=self.root, env=env, capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(process.returncode, 0)
                raw = (self.root / "commons-battery-results.nul").read_bytes()
                data = self.build(raw)
                self.assertTrue(data["complete"])
                self.assertEqual(data["conclusion"], conclusion)
                self.assertEqual(data["counts"]["completed_files"], expected_count)
                self.assertEqual(data["counts"]["failed_files"], 0)
            for path in self.files:
                (self.root / path).unlink(missing_ok=True)

    def test_workflow_uploads_report_even_when_battery_fails(self):
        text = (ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")
        self.assertIn("id: battery", text)
        self.assertIn("id: checkout", text)
        self.assertIn("--outcome \"${{ steps.battery.outcome }}\"", text)
        self.assertEqual(text.count("if: ${{ always() && steps.checkout.outcome == 'success' }}"), 2)
        self.assertIn("uses: actions/upload-artifact@v4", text)
        self.assertIn("name: battery-results-${{ github.run_id }}-${{ github.run_attempt }}", text)


if __name__ == "__main__":
    unittest.main()
