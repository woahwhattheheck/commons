#!/usr/bin/env python3
"""Guard rule-arbitrage CI against stale queued-push comparisons to moving main."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKFLOW = ROOT / ".github" / "workflows" / "flora-kag-rule-arbitrage.yml"
AUDIT = ROOT / ".github" / "scripts" / "audit_git_terminal.py"
MAIN_REFSPEC = "+refs/heads/main:refs/remotes/origin/main"


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class RuleArbitrageWorkflowQueueTests(unittest.TestCase):
    def test_push_uses_depth_independent_landed_ancestry_not_future_main_bytes(self) -> None:
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("git diff --exit-code HEAD origin/main --", yml)
        self.assertNotIn("--depth=100 origin main", yml)
        self.assertIn('git rev-parse --is-shallow-repository', yml)
        self.assertIn('git fetch --quiet --filter=blob:none --unshallow origin "$MAIN_REFSPEC"', yml)
        self.assertIn(
            'audit_git_terminal.py --target-ref origin/main --expected-commit "$EXPECTED_COMMIT"',
            yml,
        )
        self.assertIn(
            "--required-path revenue/kaggriculture/cloud-rule-arbitrage/candidate.py",
            yml,
        )

    def test_pull_request_diff_check_and_literal_head_checkout_are_preserved(self) -> None:
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("ref: ${{ github.event.pull_request.head.sha || github.sha }}", yml)
        self.assertIn('test "$(git rev-parse HEAD)" = "$EXPECTED_COMMIT"', yml)
        self.assertIn(
            'git diff --check "${{ github.event.pull_request.base.sha }}" HEAD',
            yml,
        )

    def test_regression_contract_is_watched_and_executed(self) -> None:
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(yml.count('"test_flora_kag_rule_arbitrage_workflow_queue.py"'), 2)
        self.assertEqual(
            yml.count("python -B test_flora_kag_rule_arbitrage_workflow_queue.py"),
            1,
        )

    def test_unshallow_repairs_more_than_100_commit_queue_gap(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            source = tmp / "source"
            remote = tmp / "origin.git"
            runner = tmp / "runner"
            source.mkdir()
            _git(source, "init", "-q")
            _git(source, "config", "user.email", "queue-test@example.invalid")
            _git(source, "config", "user.name", "queue-test")
            (source / "revenue/kaggriculture/cloud-rule-arbitrage").mkdir(parents=True)
            (source / "revenue/kaggriculture/cloud-rule-arbitrage/candidate.py").write_text(
                "# candidate survives\n", encoding="utf-8"
            )
            _git(source, "add", ".")
            _git(source, "commit", "-qm", "event")
            event_commit = _git(source, "rev-parse", "HEAD").stdout.strip()

            # Keep the predecessor just beyond the old workflow's fixed history window.
            for index in range(101):
                (source / "history.txt").write_text(f"{index}\n", encoding="utf-8")
                _git(source, "add", "history.txt")
                _git(source, "commit", "-qm", f"later-{index:03d}")
            _git(source, "branch", "-M", "main")
            _git(tmp, "clone", "-q", "--bare", str(source), str(remote))

            runner.mkdir()
            _git(runner, "init", "-q")
            _git(runner, "remote", "add", "origin", remote.resolve().as_uri())
            _git(runner, "fetch", "-q", "--depth=1", "origin", event_commit)
            _git(runner, "checkout", "-q", "--detach", "FETCH_HEAD")
            self.assertEqual(_git(runner, "rev-parse", "--is-shallow-repository").stdout.strip(), "true")

            _git(runner, "fetch", "-q", "--depth=100", "origin", MAIN_REFSPEC)
            old_audit = subprocess.run(
                [
                    sys.executable,
                    str(AUDIT),
                    "--repo",
                    str(runner),
                    "--target-ref",
                    "origin/main",
                    "--expected-commit",
                    event_commit,
                    "--required-path",
                    "revenue/kaggriculture/cloud-rule-arbitrage/candidate.py",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(old_audit.returncode, 2, old_audit.stdout + old_audit.stderr)

            _git(runner, "fetch", "-q", "--unshallow", "origin", MAIN_REFSPEC)
            self.assertEqual(_git(runner, "rev-parse", "--is-shallow-repository").stdout.strip(), "false")
            repaired_audit = subprocess.run(
                [
                    sys.executable,
                    str(AUDIT),
                    "--repo",
                    str(runner),
                    "--target-ref",
                    "origin/main",
                    "--expected-commit",
                    event_commit,
                    "--required-path",
                    "revenue/kaggriculture/cloud-rule-arbitrage/candidate.py",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(repaired_audit.returncode, 0, repaired_audit.stdout + repaired_audit.stderr)


if __name__ == "__main__":
    unittest.main()
