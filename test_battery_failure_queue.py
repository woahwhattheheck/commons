#!/usr/bin/env python3
"""Offline regression coverage, including real temporary Git commits and CLI I/O."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

MODULE = Path(__file__).parent / "host" / "battery_failure_queue.py"
SPEC = importlib.util.spec_from_file_location("battery_failure_queue", MODULE)
assert SPEC is not None and SPEC.loader is not None
queue = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(queue)


def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def report_fixture() -> dict:
    rows = [{
        "path": name, "command": ["python3", "./" + name], "exit_code": exit_code,
        "source_blob_sha": blob(content), "source_in_checkout_commit": True,
    } for name, content, exit_code in (
        ("test_same.py", b"same\n", 1),
        ("test_changed.py", b"old\n", 1),
        ("test_removed.py", b"removed\n", 1),
        ("test_pass.py", b"passed\n", 0),
    )]
    return {
        "schema": queue.REPORT_SCHEMA, "repository": "example/fixture",
        "run_id": "123", "run_attempt": "1", "checkout_sha": "a" * 40,
        "complete": True, "conclusion": "FAILED", "workflow_outcome": "failure",
        "counts": {"completed_files": 4, "passed_files": 1,
                   "failed_files": 3, "unresolved_source_files": 0},
        "results": rows, "problems": [],
    }


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.report = report_fixture()
        self.digest = "f" * 64

    def test_report_only_preserves_counts_and_sorted_failures(self):
        out = queue.build_queue(self.report, self.digest)
        self.assertEqual(out["retained_failed_files"], 3)
        self.assertEqual(out["source_state_counts"]["NOT_COMPARED"], 3)
        self.assertEqual([r["path"] for r in out["failures"]],
                         ["test_changed.py", "test_removed.py", "test_same.py"])
        self.assertFalse(out["tests_executed"])
        self.assertEqual(out["current_test_status"], "NOT_MEASURED")
        self.assertTrue(all(r["rerun_required"] for r in out["failures"]))
        self.assertEqual(out["report"]["counts"], self.report["counts"])

    def test_input_and_commands_are_not_mutated_or_aliased(self):
        before = copy.deepcopy(self.report)
        out = queue.build_queue(self.report, self.digest)
        out["failures"][0]["recorded_command"].append("changed")
        out["report"]["counts"]["failed_files"] = 100
        self.assertEqual(self.report, before)

    def test_incomplete_report_stays_incomplete(self):
        self.report["complete"] = False
        self.report["problems"] = ["runner stopped"]
        out = queue.build_queue(self.report, self.digest)
        self.assertFalse(out["report"]["complete"])
        self.assertEqual(out["report"]["problems"], ["runner stopped"])

    def test_unresolved_source_never_becomes_same_blob(self):
        row = self.report["results"][0]
        row["source_in_checkout_commit"] = False
        self.report["counts"]["unresolved_source_files"] = 1
        out = queue.build_queue(self.report, self.digest, "b" * 40,
                                {row["path"]: row["source_blob_sha"]})
        item = next(r for r in out["failures"] if r["path"] == row["path"])
        self.assertEqual(item["source_state"], "UNRESOLVED_RECORDED_SOURCE")

    def test_unresolved_missing_blob_is_preserved(self):
        row = self.report["results"][0]
        row["source_blob_sha"] = None
        row["source_in_checkout_commit"] = False
        self.report["counts"]["unresolved_source_files"] = 1
        out = queue.build_queue(self.report, self.digest)
        self.assertEqual(out["source_state_counts"]["UNRESOLVED_RECORDED_SOURCE"], 1)

    def test_duplicate_paths_rejected(self):
        self.report["results"][1]["path"] = self.report["results"][0]["path"]
        with self.assertRaisesRegex(queue.QueueError, "duplicate result path"):
            queue.validate_report(self.report)

    def test_bad_paths_rejected(self):
        for value in (None, [], 3, "", ".", "../test.py", "/test.py", "a/../b",
                      "a//b", "./test.py", "a\\b", "a\x00b"):
            with self.subTest(value=value):
                candidate = copy.deepcopy(self.report)
                candidate["results"][0]["path"] = value
                with self.assertRaises(queue.QueueError):
                    queue.validate_report(candidate)

    def test_boolean_exit_code_and_count_rejected(self):
        for field in ("exit_code", "failed_files"):
            candidate = copy.deepcopy(self.report)
            target = candidate["results"][0] if field == "exit_code" else candidate["counts"]
            target[field] = True
            with self.subTest(field=field), self.assertRaises(queue.QueueError):
                queue.validate_report(candidate)

    def test_declared_counts_must_reconcile(self):
        for key in self.report["counts"]:
            candidate = copy.deepcopy(self.report)
            candidate["counts"][key] += 1
            with self.subTest(key=key), self.assertRaisesRegex(queue.QueueError, "counts"):
                queue.validate_report(candidate)

    def test_bad_root_and_row_shapes_rejected(self):
        for candidate in (None, [], True, "report"):
            with self.subTest(candidate=candidate), self.assertRaises(queue.QueueError):
                queue.validate_report(candidate)
        for field, value in (("results", {}), ("results", [None]), ("counts", []),
                             ("complete", 1), ("run_id", 123), ("run_attempt", "0"),
                             ("checkout_sha", "a" * 40 + "\n"), ("problems", "oops")):
            candidate = copy.deepcopy(self.report)
            candidate[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(queue.QueueError):
                queue.validate_report(candidate)

    def test_invalid_commands_and_provenance_rejected(self):
        for field, value in (("command", "python3 test.py"), ("command", []),
                             ("command", [False]), ("source_blob_sha", "x" * 40),
                             ("source_blob_sha", None), ("source_in_checkout_commit", 1)):
            candidate = copy.deepcopy(self.report)
            candidate["results"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(queue.QueueError):
                queue.validate_report(candidate)

    def test_comparison_requires_valid_paired_commit_and_tree(self):
        for sha, tree in ((None, {}), ("a" * 40, None), ("abc", {}),
                          ("b" * 40, {"test.py": "bad"}), ("b" * 40, [])):
            with self.subTest(sha=sha, tree=tree), self.assertRaises(queue.QueueError):
                queue.build_queue(self.report, self.digest, sha, tree)

    def test_empty_success_report_does_not_claim_current_success(self):
        self.report["results"] = []
        self.report["counts"] = {key: 0 for key in self.report["counts"]}
        self.report["conclusion"] = "PASSED"
        self.report["workflow_outcome"] = "success"
        out = queue.build_queue(self.report, self.digest)
        self.assertEqual(out["failures"], [])
        self.assertEqual(out["current_test_status"], "NOT_MEASURED")

    def test_nonzero_and_signal_exit_codes_are_retained(self):
        self.report["results"][0]["exit_code"] = -9
        out = queue.build_queue(self.report, self.digest)
        self.assertEqual(next(r for r in out["failures"] if r["path"] == "test_same.py")
                         ["recorded_exit_code"], -9)

    def test_exact_bytes_digest_and_immutable_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            raw = json.dumps(self.report, indent=3).encode() + b"\n\n"
            path.write_bytes(raw)
            loaded, digest = queue.load_report(path)
            self.assertEqual(loaded, self.report)
            self.assertEqual(digest, hashlib.sha256(raw).hexdigest())
            self.assertEqual(path.read_bytes(), raw)

    def test_invalid_json_duplicate_keys_and_nonfinite_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            for raw in (b"\xff", b"{", b'{"a":1,"a":2}', b'{"a":NaN}',
                        b'{"a":Infinity}', b'{"a":-Infinity}'):
                path.write_bytes(raw)
                with self.subTest(raw=raw), self.assertRaises(queue.QueueError):
                    queue.load_report(path)

    def test_report_size_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            path.write_bytes(b" " * 100)
            with mock.patch.object(queue, "MAX_REPORT_BYTES", 20):
                with self.assertRaisesRegex(queue.QueueError, "exceeds"):
                    queue.load_report(path)


class GitAndCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Offline fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        for name, raw in (("test_same.py", b"same\n"), ("test_changed.py", b"old\n"),
                          ("test_removed.py", b"removed\n"), ("test_pass.py", b"passed\n"),
                          ("dependency.py", b"v1\n")):
            (self.root / name).write_bytes(raw)
        self.commit("base")
        self.base = self.git("rev-parse", "HEAD").strip()
        self.report = report_fixture()
        self.report["checkout_sha"] = self.base
        (self.root / "test_changed.py").write_text("new\n")
        (self.root / "test_removed.py").unlink()
        (self.root / "dependency.py").write_text("v2\n")
        self.commit("comparison")
        self.head = self.git("rev-parse", "HEAD").strip()
        self.path = self.root / "retained.json"
        self.path.write_text(json.dumps(self.report))

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              capture_output=True, text=True).stdout

    def commit(self, message):
        self.git("add", ".")
        self.git("-c", "commit.gpgsign=false", "commit", "-qm", message)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(MODULE), str(self.path), *args],
                              capture_output=True, text=True, timeout=10)

    def test_real_git_classifies_same_changed_and_absent(self):
        sha, tree = queue.git_snapshot(self.root, "HEAD")
        out = queue.build_queue(self.report, "f" * 64, sha, tree)
        self.assertEqual(sha, self.head)
        states = {r["path"]: r["source_state"] for r in out["failures"]}
        self.assertEqual(states, {"test_same.py": "SAME_TEST_BLOB",
                                 "test_changed.py": "CHANGED_TEST_BLOB",
                                 "test_removed.py": "ABSENT_AT_COMPARISON"})
        self.assertEqual(tree["test_same.py"], blob(b"same\n"))
        self.assertEqual(out["current_test_status"], "NOT_MEASURED")

    def test_dirty_worktree_is_not_compared_or_changed(self):
        (self.root / "test_same.py").write_text("dirty\n")
        before = self.git("status", "--porcelain")
        sha, tree = queue.git_snapshot(self.root, "HEAD")
        self.assertEqual(sha, self.head)
        self.assertEqual(tree["test_same.py"], blob(b"same\n"))
        self.assertEqual(self.git("status", "--porcelain"), before)
        self.assertEqual((self.root / "test_same.py").read_text(), "dirty\n")

    def test_requested_historical_commit_is_used(self):
        result = self.cli("--root", str(self.root), "--ref", self.base)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = json.loads(result.stdout)
        self.assertEqual(out["comparison_sha"], self.base)
        self.assertEqual(out["source_state_counts"]["SAME_TEST_BLOB"], 3)

    def test_ref_is_resolved_once_before_tree_read(self):
        calls = []
        original = queue._git
        def observe(root, *args):
            calls.append(args)
            return original(root, *args)
        with mock.patch.object(queue, "_git", side_effect=observe):
            queue.git_snapshot(self.root, "HEAD")
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1][-1], self.head)
        self.assertNotIn("HEAD", calls[1])

    def test_cli_output_is_repeatable_and_input_unchanged(self):
        raw = self.path.read_bytes()
        one = self.cli("--root", str(self.root))
        two = self.cli("--root", str(self.root))
        self.assertEqual(one.returncode, 0, one.stderr)
        self.assertEqual(one.stdout, two.stdout)
        self.assertEqual(self.path.read_bytes(), raw)
        self.assertEqual(json.loads(one.stdout)["report"]["sha256"],
                         hashlib.sha256(raw).hexdigest())

    def test_recorded_commands_are_never_executed(self):
        sentinel = self.root / "must-not-exist"
        self.report["results"][0]["command"] = [
            sys.executable, "-c", f"from pathlib import Path; Path({str(sentinel)!r}).touch()"]
        self.path.write_text(json.dumps(self.report))
        result = self.cli("--report-only", "--root", str(self.root / "nonexistent"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(sentinel.exists())
        self.assertIsNone(json.loads(result.stdout)["comparison_sha"])

    def test_bad_revision_and_nonrepository_fail_without_json(self):
        for args in (("--root", str(self.root), "--ref", "missing-ref"),
                     ("--root", str(self.root / "missing")),
                     ("--root", str(self.root), "--ref=--help")):
            with self.subTest(args=args):
                result = self.cli(*args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertIn("BATTERY QUEUE ERROR:", result.stderr)

    def test_bad_report_cli_fails_without_traceback_or_success(self):
        self.path.write_text('{"bad":true}')
        result = self.cli("--report-only")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
