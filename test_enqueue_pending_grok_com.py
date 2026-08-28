#!/usr/bin/env python3
"""Queue pending GROK.COM actions from job-watchdog, not from action-executor."""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import action_executor as ae
import enqueue_pending_grok_com as enqueue

WORKFLOW = Path(__file__).resolve().parent / ".github/workflows/job-watchdog.yml"


class EnqueuePendingGrokComTests(unittest.TestCase):
    def init_repo(self, root):
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
        (root / "seed.txt").write_text("seed\n", encoding="utf-8")
        subprocess.run(["git", "add", "seed.txt"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "seed"], cwd=root, check=True)

    def test_writes_wake_jobs_only_for_grok_target(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.init_repo(root)
            posts = root / "p"
            results = root / "actions" / "results"
            posts.mkdir()
            results.mkdir(parents=True)
            (posts / "grok-enqueue-job-0001.md").write_text(
                "from: OPEN\nto: TOOLS\nid: grok-enqueue-job-0001\nkind: ACTION\nact: BUILD\ntarget: GROK.COM\n\n---\n\nBUILD\ntarget: GROK.COM\n\nexact prompt bytes\n",
                encoding="utf-8",
            )
            (posts / "shell-enqueue-job-0001.md").write_text(
                "from: OPEN\nto: TOOLS\nid: shell-enqueue-job-0001\nkind: ACTION\nact: RUN\ntarget: out.txt\n\n---\n\nRUN\ntarget: out.txt\n\necho hi\n",
                encoding="utf-8",
            )
            with (
                mock.patch.object(ae, "ROOT", root),
                mock.patch.object(ae, "POSTS", posts),
                mock.patch.object(ae, "RESULTS", results),
            ):
                report = enqueue.enqueue_pending_grok_com()
            self.assertTrue(report["ok"])
            self.assertEqual(report["queued"], ["wake_jobs/grok-enqueue-job-0001.json"])
            self.assertTrue((root / "wake_jobs" / "grok-enqueue-job-0001.json").is_file())
            self.assertFalse((root / "wake_jobs" / "shell-enqueue-job-0001.json").is_file())
            with (
                mock.patch.object(ae, "ROOT", root),
                mock.patch.object(ae, "POSTS", posts),
                mock.patch.object(ae, "RESULTS", results),
            ):
                again = enqueue.enqueue_pending_grok_com()
            self.assertEqual(again["queued"], ["wake_jobs/grok-enqueue-job-0001.json"])
            job = json.loads((root / "wake_jobs" / "grok-enqueue-job-0001.json").read_text(encoding="utf-8"))
            self.assertEqual(job["checkpoint"]["execution"]["submission_state"], "NOT_SUBMITTED")

    def test_workflow_queues_pending_grok_com_before_land(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("enqueue_pending_grok_com.py", text)
        self.assertIn("fetch-depth: 0", text)
        before_land, _sep, _rest = text.partition("name: land job state on main only")
        self.assertIn("enqueue_pending_grok_com.py", before_land)
        self.assertGreater(
            before_land.rfind("enqueue_pending_grok_com.py"),
            before_land.find("python3 -m harness_wake --tick"),
        )
        _checkout, _sep, after_checkout = text.partition("uses: actions/checkout@v4")
        self.assertIn("fetch-depth: 0", after_checkout.split("name:", 1)[0])


if __name__ == "__main__":
    raise SystemExit(unittest.main())
