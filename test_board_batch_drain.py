#!/usr/bin/env python3
"""Slack issue bursts coalesce, skip carrier polling, and drain in one run."""

import json
import os
from pathlib import Path
import unittest
from unittest import mock

import board_ingest
import yaml


ROOT = Path(__file__).resolve().parent


class BoardBatchDrainTest(unittest.TestCase):
    def test_workflow_yaml_parses_with_slack_carrier_condition(self):
        raw = (ROOT / ".github/workflows/commons-board.yml").read_text(encoding="utf-8")
        parsed = yaml.safe_load(raw)

        steps = parsed["jobs"]["ingest"]["steps"]
        poll = next(step for step in steps if step.get("name") == "poll ntfy on ordinary issue runs")
        self.assertEqual(
            poll["if"],
            "${{ github.event_name == 'issues' && !contains(github.event.issue.body, "
            "'carrier: slack-connector') }}",
        )

    def test_workflow_coalesces_only_slack_connector_issue_runs(self):
        raw = (ROOT / ".github/workflows/commons-board.yml").read_text(encoding="utf-8")
        self.assertIn("contains(github.event.issue.body, 'carrier: slack-connector')", raw)
        self.assertIn("commons-board-ingest-${{", raw)
        self.assertIn("'slack-batch'", raw)
        self.assertIn("cancel-in-progress: false", raw)

    def test_workflow_repair_push_wakes_the_recovery_sweep(self):
        raw = (ROOT / ".github/workflows/commons-board.yml").read_text(encoding="utf-8")
        self.assertIn("push:\n    branches: [main]\n    paths:\n      - \".github/workflows/commons-board.yml\"", raw)

        old = os.environ.get("GITHUB_EVENT_NAME")
        os.environ["GITHUB_EVENT_NAME"] = "push"
        issue = {
            "number": 1,
            "title": "repair-wake-0001",
            "body": "repair wake body",
            "labels": [{"name": "board"}],
            "created_at": "2026-09-02T00:00:00Z",
        }
        try:
            with mock.patch.object(board_ingest, "_gh_api_paged", return_value=[issue]), \
                 mock.patch.object(board_ingest, "write_post", return_value="wrote"):
                planned = board_ingest.sweep_collect()
        finally:
            if old is None:
                os.environ.pop("GITHUB_EVENT_NAME", None)
            else:
                os.environ["GITHUB_EVENT_NAME"] = old

        self.assertEqual(len(planned), 1)

    def test_publisher_uses_independent_standard_arm_runner_pool(self):
        raw = (ROOT / ".github/workflows/commons-board.yml").read_text(encoding="utf-8")
        self.assertIn("runs-on: ubuntu-24.04-arm", raw)
        self.assertIn("runner_id=0 beyond both recovery cycles", raw)
        self.assertIn("does not allocate the owner's laptop runner", raw)

    def test_slack_connector_issue_run_does_not_poll_public_carriers(self):
        old = os.environ.get("GITHUB_EVENT_NAME")
        old_path = os.environ.get("GITHUB_EVENT_PATH")
        event_path = ROOT / "._test_slack_connector_issue.json"
        event_path.write_text(
            json.dumps({
                "issue": {
                    "number": 1,
                    "body": "from: PLAYER1\nto: TABLE\nid: slack-batch-0001\ncarrier: slack-connector\n\n---\n\nhi\n",
                }
            }),
            encoding="utf-8",
        )
        os.environ["GITHUB_EVENT_NAME"] = "issues"
        os.environ["GITHUB_EVENT_PATH"] = str(event_path)
        try:
            with mock.patch.object(board_ingest, "ingest_ntfy", side_effect=AssertionError("carrier poll")), \
                 mock.patch.object(board_ingest, "ingest_github_event", return_value=1), \
                 mock.patch.object(board_ingest, "sweep_collect", return_value=[]), \
                 mock.patch.object(board_ingest, "rebuild"), \
                 mock.patch.object(board_ingest, "list_posts", return_value=[]):
                self.assertEqual(board_ingest._ingest_and_maybe_publish(False), 0)
        finally:
            event_path.unlink(missing_ok=True)
            if old is None:
                os.environ.pop("GITHUB_EVENT_NAME", None)
            else:
                os.environ["GITHUB_EVENT_NAME"] = old
            if old_path is None:
                os.environ.pop("GITHUB_EVENT_PATH", None)
            else:
                os.environ["GITHUB_EVENT_PATH"] = old_path

    def test_one_issue_run_drains_more_than_old_forty_record_cap(self):
        old = os.environ.get("GITHUB_EVENT_NAME")
        os.environ["GITHUB_EVENT_NAME"] = "issues"
        issues = [
            {
                "number": n,
                "title": "batch-%04d" % n,
                "body": "batch body %d" % n,
                "labels": [{"name": "board"}],
                "created_at": "2026-08-27T00:00:00Z",
            }
            for n in range(120)
        ]
        wrote = []

        def fake_write(_src, _dest, mid, _text, **_kwargs):
            wrote.append(mid)
            return "wrote"

        try:
            with mock.patch.object(board_ingest, "_gh_api_paged", return_value=issues), \
                 mock.patch.object(board_ingest, "write_post", side_effect=fake_write):
                planned = board_ingest.sweep_collect()
        finally:
            if old is None:
                os.environ.pop("GITHUB_EVENT_NAME", None)
            else:
                os.environ["GITHUB_EVENT_NAME"] = old

        self.assertGreaterEqual(board_ingest.MAX_SWEEP_NEW, 120)
        self.assertEqual(len(wrote), 120)
        self.assertEqual(len(planned), 120)


if __name__ == "__main__":
    unittest.main()
