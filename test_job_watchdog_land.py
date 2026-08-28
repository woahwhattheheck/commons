#!/usr/bin/env python3
"""Regression for job-watchdog land losing a moving-main push race.

Run 33186268839 on SHA 7bd5c37b8a8ec096c154903cbb1af17bce5090f1 rebased,
then `git push origin HEAD:main` was rejected (`fetch first`) because
another land hit main in the gap. Cite:
woahwhattheheck/commons:job-watchdog:7bd5c37b8a8ec096c154903cbb1af17bce5090f1:land job state on main only
"""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

from harness_wake.land import COMMIT_MESSAGE, is_push_race, land


ROOT = Path(__file__).resolve().parent
WORKFLOW = ROOT / ".github/workflows/job-watchdog.yml"

# Exact stderr from https://github.com/woahwhattheheck/commons/actions/runs/33186268839
RUN_33186268839_STDERR = """\
To https://github.com/woahwhattheheck/commons
 ! [rejected]            HEAD -> main (fetch first)
error: failed to push some refs to 'https://github.com/woahwhattheheck/commons'
hint: Updates were rejected because the remote contains work that you do not
hint: have locally. This is usually caused by another repository pushing to
hint: the same ref. If you want to integrate the remote changes, use
hint: 'git pull' before pushing again.
hint: See the 'Note about fast-forwards' in 'git push --help' for details.
"""


class FakeGit:
    def __init__(
        self,
        *,
        cached_dirty: bool = True,
        push_results: list[tuple[int, str]] | None = None,
        rebase_code: int = 0,
    ):
        self.calls: list[list[str]] = []
        self.cached_dirty = cached_dirty
        self.push_results = list(push_results or [(0, "")])
        self.rebase_code = rebase_code
        self.slept: list[float] = []

    def __call__(self, args, **kwargs):
        cmd = list(args)
        self.calls.append(cmd)
        verb = cmd[1] if len(cmd) > 1 else ""
        stdout, stderr, code = "", "", 0
        if verb == "diff":
            code = 1 if self.cached_dirty else 0
        elif verb == "commit":
            stdout = "[main deadbeef] %s" % COMMIT_MESSAGE
        elif verb == "push":
            code, stderr = self.push_results.pop(0)
        elif verb == "rebase" and "--abort" not in cmd:
            code = self.rebase_code
            if code:
                stderr = "CONFLICT (content): merge conflict in wake_jobs/x.json"
        return subprocess.CompletedProcess(cmd, code, stdout, stderr)

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)

    def verbs(self) -> list[str]:
        return [cmd[1] for cmd in self.calls if len(cmd) > 1]


class JobWatchdogLandTests(unittest.TestCase):
    def test_workflow_lands_through_retrying_helper(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 -m harness_wake.land", text)
        land_step = text.split("name: land job state on main only", 1)[1]
        self.assertNotIn("git pull --rebase origin main", land_step)
        self.assertNotIn("git push origin HEAD:main", land_step)
        self.assertNotIn("--force", land_step)
        self.assertIn("github.ref == 'refs/heads/main'", land_step.split("run:", 1)[0])

    def test_quiet_tree_does_not_push(self):
        git = FakeGit(cached_dirty=False)
        result = land(run=git, sleep=git.sleep)
        self.assertEqual(result["state"], "QUIET")
        self.assertTrue(result["ok"])
        self.assertEqual(git.verbs(), ["add", "diff"])

    def test_first_push_success_lands_once(self):
        git = FakeGit(push_results=[(0, "")])
        result = land(run=git, sleep=git.sleep)
        self.assertEqual(result, {"ok": True, "state": "LANDED", "attempts": 1})
        self.assertEqual(git.verbs(), ["add", "diff", "commit", "push"])
        self.assertEqual(git.slept, [])

    def test_run_33186268839_race_retries_and_lands(self):
        git = FakeGit(push_results=[(1, RUN_33186268839_STDERR), (0, "")])
        result = land(run=git, sleep=git.sleep)
        self.assertTrue(is_push_race(subprocess.CompletedProcess(
            ["git", "push"], 1, "", RUN_33186268839_STDERR
        )))
        self.assertEqual(result, {"ok": True, "state": "LANDED", "attempts": 2})
        self.assertEqual(
            git.verbs(),
            ["add", "diff", "commit", "push", "fetch", "rebase", "push"],
        )
        self.assertEqual(git.slept, [3])
        joined = " ".join(" ".join(cmd) for cmd in git.calls)
        self.assertNotIn("--force", joined)

    def test_non_race_push_failure_does_not_retry(self):
        git = FakeGit(push_results=[(1, "error: permission denied")])
        result = land(run=git, sleep=git.sleep)
        self.assertEqual(result["state"], "PUSH_FAILED")
        self.assertFalse(result["ok"])
        self.assertEqual(result["attempts"], 1)
        self.assertEqual(git.verbs(), ["add", "diff", "commit", "push"])
        self.assertEqual(git.slept, [])

    def test_rebase_conflict_aborts_without_force(self):
        git = FakeGit(
            push_results=[(1, RUN_33186268839_STDERR)],
            rebase_code=1,
        )
        result = land(run=git, sleep=git.sleep)
        self.assertEqual(result["state"], "REBASE_CONFLICT")
        self.assertFalse(result["ok"])
        self.assertEqual(
            git.verbs(),
            ["add", "diff", "commit", "push", "fetch", "rebase", "rebase"],
        )
        self.assertEqual(git.calls[-1], ["git", "rebase", "--abort"])
        joined = " ".join(" ".join(cmd) for cmd in git.calls)
        self.assertNotIn("--force", joined)

    def test_exhausted_race_reports_push_race(self):
        git = FakeGit(push_results=[
            (1, RUN_33186268839_STDERR),
            (1, RUN_33186268839_STDERR),
        ])
        result = land(attempts=2, run=git, sleep=git.sleep)
        self.assertEqual(result["state"], "PUSH_RACE")
        self.assertFalse(result["ok"])
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(git.slept, [3])
        self.assertEqual(git.verbs().count("push"), 2)
        self.assertEqual(git.verbs().count("rebase"), 2)

    def test_helper_main_prints_json_receipt(self):
        from harness_wake import land as land_mod

        git = FakeGit(cached_dirty=False)
        original = land_mod.land
        try:
            land_mod.land = lambda **_kwargs: land(run=git, sleep=git.sleep)
            code = land_mod.main([])
        finally:
            land_mod.land = original
        self.assertEqual(code, 0)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
