from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("receipt", HERE / "exact_head_exec_receipt.py")
receipt = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(receipt)


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


class ExactHeadReceiptTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.base = Path(self.td.name)
        self.root = self.base / "repo"
        self.root.mkdir()
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "test@example.invalid")
        git(self.root, "config", "user.name", "Test")
        git(self.root, "remote", "add", "origin", "https://github.com/acme/demo.git")
        (self.root / "check.py").write_text("print('ok')\n", encoding="utf-8")
        git(self.root, "add", "check.py")
        git(self.root, "commit", "-qm", "base")
        self.head = git(self.root, "rev-parse", "HEAD")
        self.plan = self.base / "plan.json"

    def tearDown(self):
        self.td.cleanup()

    def write_plan(self, commands=None, **updates):
        data = {
            "schema": receipt.PLAN_SCHEMA,
            "repo": "acme/demo",
            "head_sha": self.head,
            "commands": commands or [{
                "id": "smoke",
                "argv": [sys.executable, "check.py"],
                "timeout_seconds": 5,
            }],
        }
        data.update(updates)
        self.plan.write_text(json.dumps(data), encoding="utf-8")
        return data

    def test_clean_exact_head_passes_and_binds_repo_tree_and_logs(self):
        self.write_plan()
        report, code = receipt.execute_plan(self.root, self.plan, self.head)
        self.assertEqual(code, 0)
        self.assertEqual(report["conclusion"], "PASSED")
        self.assertEqual(report["checkout"]["repo"], "acme/demo")
        self.assertEqual(report["checkout"]["head_sha"], self.head)
        self.assertEqual(len(report["checkout"]["tree_sha"]), 40)
        self.assertEqual(report["commands"][0]["exit_code"], 0)
        self.assertEqual(len(report["commands"][0]["stdout"]["sha256"]), 64)
        self.assertEqual(len(report["commands"][0]["executable_sha256"]), 64)
        self.assertTrue(Path(report["commands"][0]["resolved_executable"]).is_absolute())
        self.assertFalse(report["safety"]["hosted_ci_replacement_claimed"])

    def test_wrong_external_head_fails_before_command(self):
        marker = self.base / "ran"
        self.write_plan([{"id":"nope","argv":[sys.executable,"-c",f"from pathlib import Path; Path({str(marker)!r}).write_text('x')"],"timeout_seconds":5}])
        with self.assertRaises(receipt.ReceiptError):
            receipt.execute_plan(self.root, self.plan, "0" * 40)
        self.assertFalse(marker.exists())

    def test_plan_head_must_match_external_head(self):
        self.write_plan(head_sha="f" * 40)
        with self.assertRaisesRegex(receipt.ReceiptError, "plan head_sha"):
            receipt.execute_plan(self.root, self.plan, self.head)

    def test_origin_repo_must_match_plan(self):
        self.write_plan(repo="evil/other")
        with self.assertRaisesRegex(receipt.ReceiptError, "origin repo"):
            receipt.execute_plan(self.root, self.plan, self.head)

    def test_credential_bearing_origin_is_supported_without_leaking_credentials(self):
        git(self.root, "remote", "set-url", "origin", "https://token:secret-value@github.com/acme/demo.git")
        self.write_plan()
        report, code = receipt.execute_plan(self.root, self.plan, self.head)
        self.assertEqual(code, 0)
        rendered = json.dumps(report)
        self.assertNotIn("secret-value", rendered)
        self.assertNotIn("token:", rendered)
        self.assertEqual(report["checkout"]["repo"], "acme/demo")

    def test_dirty_or_untracked_checkout_fails_closed(self):
        self.write_plan()
        (self.root / "scratch.txt").write_text("x", encoding="utf-8")
        with self.assertRaisesRegex(receipt.ReceiptError, "dirty"):
            receipt.execute_plan(self.root, self.plan, self.head)

    def test_ignored_input_fails_closed(self):
        (self.root / ".gitignore").write_text("cache.bin\n", encoding="utf-8")
        git(self.root, "add", ".gitignore")
        git(self.root, "commit", "-qm", "ignore")
        self.head = git(self.root, "rev-parse", "HEAD")
        (self.root / "cache.bin").write_text("runtime", encoding="utf-8")
        self.write_plan()
        with self.assertRaisesRegex(receipt.ReceiptError, "ignored"):
            receipt.execute_plan(self.root, self.plan, self.head)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unavailable")
    def test_safe_in_repo_tracked_symlink_is_supported(self):
        (self.root / "target.txt").write_text("safe", encoding="utf-8")
        os.symlink("target.txt", self.root / "alias.txt")
        git(self.root, "add", "target.txt", "alias.txt")
        git(self.root, "commit", "-qm", "symlink")
        self.head = git(self.root, "rev-parse", "HEAD")
        self.write_plan()
        report, code = receipt.execute_plan(self.root, self.plan, self.head)
        self.assertEqual(code, 0)
        self.assertEqual(report["checkout"]["tracked_symlink_count"], 1)
        self.assertEqual(report["checkout"]["unsafe_tracked_symlinks"], [])

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unavailable")
    def test_tracked_symlink_escaping_checkout_fails_closed(self):
        outside = self.base / "outside.txt"
        outside.write_text("external", encoding="utf-8")
        os.symlink(str(outside), self.root / "escape.txt")
        git(self.root, "add", "escape.txt")
        git(self.root, "commit", "-qm", "external symlink")
        self.head = git(self.root, "rev-parse", "HEAD")
        self.write_plan()
        with self.assertRaisesRegex(receipt.ReceiptError, "symlink"):
            receipt.execute_plan(self.root, self.plan, self.head)

    def test_all_command_paths_preflight_before_first_execution(self):
        marker = self.base / "should-not-run"
        self.write_plan([
            {"id":"first","argv":[sys.executable,"-c",f"from pathlib import Path; Path({str(marker)!r}).write_text('x')"],"timeout_seconds":5},
            {"id":"later","argv":[sys.executable,"-c","print('never')"],"cwd":"missing-dir","timeout_seconds":5},
        ])
        with self.assertRaisesRegex(receipt.ReceiptError, "not an ordinary directory"):
            receipt.execute_plan(self.root, self.plan, self.head)
        self.assertFalse(marker.exists())

    def test_nonzero_command_fails_receipt(self):
        self.write_plan([{"id":"red","argv":[sys.executable,"-c","raise SystemExit(7)"],"timeout_seconds":5}])
        report, code = receipt.execute_plan(self.root, self.plan, self.head)
        self.assertEqual(code, 1)
        self.assertEqual(report["conclusion"], "FAILED")
        self.assertEqual(report["commands"][0]["exit_code"], 7)

    def test_timeout_is_bounded_and_fails(self):
        self.write_plan([{"id":"slow","argv":[sys.executable,"-c","import time; time.sleep(5)"],"timeout_seconds":0.05}])
        report, code = receipt.execute_plan(self.root, self.plan, self.head)
        self.assertEqual(code, 1)
        self.assertTrue(report["commands"][0]["timed_out"])
        self.assertEqual(report["commands"][0]["exit_code"], 124)

    def test_checkout_mutation_after_command_is_detected(self):
        self.write_plan([{"id":"mutate","argv":[sys.executable,"-c","from pathlib import Path; Path('check.py').write_text('changed')"],"timeout_seconds":5}])
        report, code = receipt.execute_plan(self.root, self.plan, self.head)
        self.assertEqual(code, 1)
        self.assertTrue(report["safety"]["checkout_mutation_detected"])
        self.assertEqual(report["conclusion"], "FAILED")

    def test_sensitive_environment_is_not_inherited(self):
        self.write_plan([{"id":"env","argv":[sys.executable,"-c","import os,sys; sys.exit(0 if os.getenv('GITHUB_TOKEN') is None else 9)"],"timeout_seconds":5}])
        old = os.environ.get("GITHUB_TOKEN")
        os.environ["GITHUB_TOKEN"] = "super-secret-test-value"
        try:
            report, code = receipt.execute_plan(self.root, self.plan, self.head)
        finally:
            if old is None:
                os.environ.pop("GITHUB_TOKEN", None)
            else:
                os.environ["GITHUB_TOKEN"] = old
        self.assertEqual(code, 0)
        self.assertEqual(report["commands"][0]["exit_code"], 0)

    def test_cwd_traversal_and_windows_absolute_are_rejected(self):
        for cwd in ("../x", "a/../b", "/tmp", "C:\\temp", "a//b", "a/./b"):
            with self.subTest(cwd=cwd):
                self.write_plan([{"id":"bad","argv":[sys.executable,"check.py"],"cwd":cwd,"timeout_seconds":5}])
                with self.assertRaisesRegex(receipt.ReceiptError, "unsafe command cwd"):
                    receipt.execute_plan(self.root, self.plan, self.head)

    def test_duplicate_ids_and_boolean_timeout_reject(self):
        self.write_plan([
            {"id":"same","argv":[sys.executable,"check.py"],"timeout_seconds":5},
            {"id":"same","argv":[sys.executable,"check.py"],"timeout_seconds":5},
        ])
        with self.assertRaisesRegex(receipt.ReceiptError, "duplicate command id"):
            receipt.execute_plan(self.root, self.plan, self.head)
        self.write_plan([{"id":"bool","argv":[sys.executable,"check.py"],"timeout_seconds":True}])
        with self.assertRaisesRegex(receipt.ReceiptError, "timeout_seconds"):
            receipt.execute_plan(self.root, self.plan, self.head)

    def test_duplicate_json_keys_reject(self):
        body = '{"schema":"%s","schema":"%s","repo":"acme/demo","head_sha":"%s","commands":[]}' % (receipt.PLAN_SCHEMA, receipt.PLAN_SCHEMA, self.head)
        self.plan.write_text(body, encoding="utf-8")
        with self.assertRaisesRegex(receipt.ReceiptError, "duplicate JSON key"):
            receipt.execute_plan(self.root, self.plan, self.head)


if __name__ == "__main__":
    unittest.main()
