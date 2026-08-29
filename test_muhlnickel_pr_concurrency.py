#!/usr/bin/env python3
"""Muhlnickel PR checks coalesce; main verification belongs to the range lane."""

from __future__ import annotations

import unittest
from pathlib import Path

from test_tests_pr_concurrency import decide, github_ctx, parse_concurrency


ROOT = Path(__file__).resolve().parent
WORKFLOW = ROOT / ".github" / "workflows" / "muhlnickel-spec-guard.yml"
WORKFLOW_NAME = "muhlnickel-spec-guard"


def simulate(events, group_template, cancel_template):
    """GitHub concurrency: newest pending replaces older pending; cancel-in-progress
    may also drop the running occupant of the same group."""
    live = []
    for event in events:
        ctx = github_ctx(
            event["event_name"],
            event["run_id"],
            event.get("head_label"),
            workflow=WORKFLOW_NAME,
        )
        group, cancel = decide(group_template, cancel_template, ctx)
        run = {
            "run_id": str(event["run_id"]),
            "event_name": event["event_name"],
            "head_label": event.get("head_label"),
            "group": group,
            "cancel": cancel,
            "status": "in_progress",
        }
        for occupant in live:
            if occupant["group"] != group or occupant["status"] == "cancelled":
                continue
            if occupant["status"] == "queued":
                occupant["status"] = "cancelled"
            elif occupant["status"] == "in_progress" and cancel:
                occupant["status"] = "cancelled"
            elif occupant["status"] == "in_progress" and not cancel:
                run["status"] = "queued"
        live.append(run)
    return live


class MuhlnickelPrConcurrency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        cls.group_template, cls.cancel_template = parse_concurrency(cls.text)

    def test_workflow_keeps_pr_and_manual_triggers_only(self):
        self.assertNotRegex(self.text, r"(?m)^  push:")
        self.assertIn("\n  pull_request:\n", self.text)
        self.assertIn("\n  workflow_dispatch:\n", self.text)
        self.assertNotRegex(self.text, r"(?m)^  issues:\n    types: \[opened\]$")
        self.assertIn("github.event.pull_request.head.label", self.group_template)
        self.assertIn("github.run_id", self.group_template)
        self.assertIn("github.event_name == 'pull_request'", self.group_template)
        self.assertNotIn("github.ref", self.group_template)
        self.assertIn("github.event_name == 'pull_request'", self.cancel_template)

    def test_same_head_synchronize_shares_group_and_cancels(self):
        first = github_ctx(
            "pull_request",
            33184047999,
            "woahwhattheheck:grok/tests-pr-head-concurrency-20260828-01",
            workflow=WORKFLOW_NAME,
        )
        second = github_ctx(
            "pull_request",
            33184356598,
            "woahwhattheheck:grok/tests-pr-head-concurrency-20260828-01",
            workflow=WORKFLOW_NAME,
        )
        g1, c1 = decide(self.group_template, self.cancel_template, first)
        g2, c2 = decide(self.group_template, self.cancel_template, second)
        self.assertEqual(g1, g2)
        self.assertTrue(c1)
        self.assertTrue(c2)
        self.assertEqual(
            g1,
            "muhlnickel-spec-guard-woahwhattheheck:grok/tests-pr-head-concurrency-20260828-01",
        )

    def test_distinct_pr_heads_do_not_share_a_group(self):
        a = github_ctx(
            "pull_request",
            33184047999,
            "woahwhattheheck:grok/tests-pr-head-concurrency-20260828-01",
            workflow=WORKFLOW_NAME,
        )
        b = github_ctx(
            "pull_request",
            33184129806,
            "woahwhattheheck:grok-pixel-unify-agent-layer-20260828-04",
            workflow=WORKFLOW_NAME,
        )
        g1, _ = decide(self.group_template, self.cancel_template, a)
        g2, _ = decide(self.group_template, self.cancel_template, b)
        self.assertNotEqual(g1, g2)

    def test_unique_dispatch_and_other_events_keep_run_id_groups(self):
        dispatch = github_ctx("workflow_dispatch", 5001, workflow=WORKFLOW_NAME)
        issues = github_ctx("issues", 5002, workflow=WORKFLOW_NAME)
        groups = []
        for ctx in (dispatch, issues):
            group, cancel = decide(self.group_template, self.cancel_template, ctx)
            groups.append(group)
            self.assertFalse(cancel)
            self.assertTrue(group.startswith("muhlnickel-spec-guard-"))
            self.assertIn(ctx["github"]["run_id"], group)
        self.assertEqual(len(set(groups)), 2)

    def test_event_simulation_cancels_only_stale_pr_synchronize(self):
        live = simulate(
            [
                {
                    "event_name": "pull_request",
                    "run_id": 33184047999,
                    "head_label": "woahwhattheheck:grok/tests-pr-head-concurrency-20260828-01",
                },
                {
                    "event_name": "pull_request",
                    "run_id": 33184356598,
                    "head_label": "woahwhattheheck:grok/tests-pr-head-concurrency-20260828-01",
                },
                {"event_name": "workflow_dispatch", "run_id": 5001},
                {"event_name": "issues", "run_id": 5002},
                {
                    "event_name": "pull_request",
                    "run_id": 33184129806,
                    "head_label": "woahwhattheheck:grok-pixel-unify-agent-layer-20260828-04",
                },
            ],
            self.group_template,
            self.cancel_template,
        )
        by_id = {row["run_id"]: row for row in live}
        self.assertEqual(by_id["33184047999"]["status"], "cancelled")
        self.assertEqual(by_id["33184356598"]["status"], "in_progress")
        for run_id in ("5001", "5002", "33184129806"):
            self.assertEqual(by_id[run_id]["status"], "in_progress", run_id)
        self.assertEqual(
            {row["run_id"] for row in live if row["status"] == "cancelled"},
            {"33184047999"},
        )


if __name__ == "__main__":
    unittest.main()
