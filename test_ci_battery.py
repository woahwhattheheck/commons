#!/usr/bin/env python3
"""Execute the portable CI runner against small real Git checkouts."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "host/ci_battery.py"


class CloudBatteryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.out = Path(self.temp.name) / "output"
        self.git("init", "-q")
        self.git("config", "user.name", "CI Test")
        self.git("config", "user.email", "ci-test@example.invalid")
        self.write("test_a.py", "pass\n")
        self.write("infra/nested/test_b.py", "pass\n")
        self.write("nested/test_ignored.py", "raise SystemExit(99)\n")
        self.commit()

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        self.sha = self.git("rev-parse", "HEAD")

    def run_ci(self, *args, environ=None):
        return subprocess.run([sys.executable, str(RUNNER), "--root", str(self.root),
                               "--output-dir", str(self.out), *args], cwd=ROOT,
                              env=environ, capture_output=True, text=True, timeout=20)

    def report(self):
        return json.loads((self.out / "report.json").read_text())

    def test_real_suite_and_commit_evidence_without_actions_environment(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith(("GITHUB_", "RUNNER_", "CIRRUS_"))}
        env["DO_NOT_EXPORT_SECRET"] = "ci-private-sentinel"
        result = self.run_ci(environ=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = self.report()
        self.assertEqual(report["conclusion"], "PASSED")
        self.assertEqual(report["checkout_sha"], self.sha)
        self.assertEqual(report["counts"]["completed_files"], 2)
        self.assertEqual(report["scope"]["kind"], "full")
        self.assertEqual(report["scope"]["planned_files"], 2)
        self.assertFalse(report["execution"]["worktree_dirty_at_start"])
        self.assertEqual(report["run_id"], "")
        self.assertNotIn("ci-private-sentinel", json.dumps(report))
        for row in report["results"]:
            self.assertEqual(row["source_blob_sha"], self.git("rev-parse", self.sha + ":" + row["path"]))

    @unittest.skipUnless(shutil.which("node"), "requires Node")
    def test_node_failure_does_not_hide_later_node_test(self):
        self.write("test_c.js", "process.exit(7);\n")
        self.write("test_d.js", "process.exit(0);\n")
        self.commit()
        self.assertEqual(self.run_ci().returncode, 1)
        report = self.report()
        self.assertEqual(report["conclusion"], "FAILED")
        self.assertEqual(report["counts"]["completed_files"], 4)
        codes = {row["path"]: row["exit_code"] for row in report["results"]}
        self.assertEqual(codes["test_c.js"], 7)
        self.assertEqual(codes["test_d.js"], 0)

    def test_selected_scope_never_claims_full_battery(self):
        self.write("test_a.py", "raise SystemExit(6)\n")
        self.commit()
        self.assertEqual(self.run_ci("--test", "infra/nested/test_b.py").returncode, 0)
        report = self.report()
        self.assertEqual(report["scope"]["kind"], "selected")
        self.assertEqual(report["counts"]["completed_files"], 1)
        self.assertEqual(report["scope"]["discovered_files"], 2)
        self.assertEqual(report["results"][0]["path"], "infra/nested/test_b.py")

    def test_shards_partition_discovery_exactly_once(self):
        self.write("test_c.py", "pass\n")
        self.commit()
        paths = []
        for index in range(2):
            result = self.run_ci("--shard-count", "2", "--shard-index", str(index))
            self.assertEqual(result.returncode, 0, result.stderr)
            report = self.report()
            self.assertEqual(report["scope"]["kind"], "shard")
            paths.extend(row["path"] for row in report["results"])
        self.assertEqual(sorted(paths), ["infra/nested/test_b.py", "test_a.py", "test_c.py"])

    def test_empty_checkout_is_not_a_passing_run(self):
        (self.root / "test_a.py").unlink()
        (self.root / "infra/nested/test_b.py").unlink()
        self.commit()
        self.assertEqual(self.run_ci().returncode, 1)
        self.assertEqual(self.report()["conclusion"], "NO_TESTS")

    def test_timeout_keeps_later_test_and_nonzero_evidence(self):
        self.write("infra/nested/test_b.py", "import time; time.sleep(30)\n")
        self.commit()
        self.assertEqual(self.run_ci("--timeout", "0.3").returncode, 1)
        report = self.report()
        self.assertEqual(report["conclusion"], "FAILED")
        codes = {row["path"]: row["exit_code"] for row in report["results"]}
        self.assertEqual(codes, {"infra/nested/test_b.py": 124, "test_a.py": 0})

    @unittest.skipUnless(os.name == "posix", "POSIX process groups")
    def test_timeout_stops_child_process_group(self):
        marker = Path(self.temp.name) / "orphan.txt"
        child = "import time; from pathlib import Path; time.sleep(0.8); Path(" + repr(str(marker)) + ").write_text('orphan')"
        self.write("test_a.py", "import subprocess, sys, time\nsubprocess.Popen([sys.executable, '-c', " + repr(child) + "])\ntime.sleep(30)\n")
        self.commit()
        self.assertEqual(self.run_ci("--test", "test_a.py", "--timeout", "0.3").returncode, 1)
        # A fresh bounded process gives the former child enough time to write.
        subprocess.run([sys.executable, "-c", "import time; time.sleep(0.9)"], check=True)
        self.assertFalse(marker.exists())

    @unittest.skipUnless(os.name == "posix", "POSIX signal exit")
    def test_signal_exit_is_preserved_in_report(self):
        self.write("test_a.py", "import os, signal; os.kill(os.getpid(), signal.SIGTERM)\n")
        self.commit()
        self.assertEqual(self.run_ci().returncode, 1)
        report = self.report()
        self.assertEqual(report["conclusion"], "FAILED")
        self.assertEqual({r["path"]: r["exit_code"] for r in report["results"]}["test_a.py"], 143)

    def test_unknown_file_and_invalid_shards_do_not_execute(self):
        for args in (("--test", "missing.py"), ("--shard-count", "0"),
                     ("--shard-count", "2", "--shard-index", "2"), ("--timeout", "nan")):
            with self.subTest(args=args):
                self.assertEqual(self.run_ci(*args).returncode, 2)
                self.assertFalse(self.out.exists())

    def test_non_git_directory_does_not_reuse_previous_success(self):
        self.assertEqual(self.run_ci().returncode, 0)
        shutil.rmtree(self.root / ".git")
        self.assertEqual(self.run_ci().returncode, 2)
        self.assertEqual(self.report()["conclusion"], "INCOMPLETE")
        self.assertEqual(self.report()["counts"]["completed_files"], 0)


if __name__ == "__main__":
    unittest.main()
