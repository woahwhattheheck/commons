"""FLINT MEASURED: ntfy 200 + ACCEPTED_DURABILITY_PENDING is not a p/ page.

Spark FastSubmit used to return ACCEPTED after ntfy HTTP 200 even when the
packed envelope was over NTFY_MAX. Ingest then records INGEST_ERROR
unparseable-or-oversize and never writes p/{id}.md. Law: ntfy 200 is not a post.

The live event 2EiiAnFpfde5 was under cap. The silent drop was issue ingest
skipping ntfy entirely. Ordinary issue runs poll via host.ntfy_issue_poll
before the canonical board_ingest.py --publish line. Slack-connector bursts
still skip.

Do not remint Contents-API receipt 07fa3bee / fable-puzzle71-organs-fold-tick.
Do not PUT board_ingest.py (175KB Contents PUTs have truncated it).
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import commons_mcp as cm
from api import mcp
from host.ntfy_issue_poll import poll_ordinary_issue_ntfy, skip_ntfy_on_slack_connector_issue

ROOT = Path(__file__).resolve().parent


class SparkRejectsOversizeBeforeNtfyHttp(unittest.TestCase):
    def test_packed_over_ntfy_max_is_not_accepted_durability_pending(self) -> None:
        payload = {
            "id": "cursor-ntfy-append-post-silent-drop-20260902-01",
            "body": "x" * (cm.NTFY_MAX + 200),
        }
        packed = cm._canonical_json(payload).encode("utf-8")
        self.assertGreater(len(packed), cm.NTFY_MAX)
        gw = mcp.FAST_SUBMIT_GATEWAY
        with mock.patch.object(gw.carrier, "submit") as submit:
            with self.assertRaises(cm.CommonsError) as caught:
                gw._submit(payload)
        submit.assert_not_called()
        err = caught.exception
        self.assertEqual(err.code, "CARRIER_LIMIT")
        self.assertEqual(err.state, "NOT_SENT")
        self.assertNotEqual(err.state, "ACCEPTED_DURABILITY_PENDING")
        self.assertIn("3,900", err.message)

    def test_packed_under_ntfy_max_still_hits_carrier(self) -> None:
        payload = {
            "id": "under-cap",
            "body": "y",
        }
        packed = cm._canonical_json(payload).encode("utf-8")
        self.assertLessEqual(len(packed), cm.NTFY_MAX)
        gw = mcp.FAST_SUBMIT_GATEWAY
        with mock.patch.object(
            gw.carrier, "submit", return_value={"ok": True, "event_id": "evt"}
        ) as submit:
            out = gw._submit(payload)
        submit.assert_called_once()
        self.assertEqual(out["state"], "ACCEPTED_DURABILITY_PENDING")
        self.assertEqual(out["carrier"]["event_id"], "evt")
        self.assertFalse(out["durable"])


class OrdinaryIssueNtfyPoll(unittest.TestCase):
    def test_workflow_keeps_canonical_publisher_and_adds_ordinary_issue_poll(self) -> None:
        raw = (ROOT / ".github/workflows/commons-board.yml").read_text(encoding="utf-8")
        self.assertIn("python3 board_ingest.py --publish", raw)
        self.assertIn("run: python3 -m host.ntfy_issue_poll", raw)
        self.assertLess(
            raw.find("run: python3 -m host.ntfy_issue_poll"),
            raw.find("python3 board_ingest.py --publish"),
        )
        self.assertIn("!contains(github.event.issue.body, 'carrier: slack-connector')", raw)

    def test_ordinary_issues_event_polls_ntfy(self) -> None:
        import board_ingest

        event = {
            "issue": {
                "number": 7372,
                "title": "ordinary issue",
                "body": "no slack connector needle here",
            }
        }
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(event, fh)
            with mock.patch.dict(
                os.environ,
                {"GITHUB_EVENT_NAME": "issues", "GITHUB_EVENT_PATH": path},
                clear=False,
            ):
                self.assertFalse(skip_ntfy_on_slack_connector_issue(_read_for_test))
                with mock.patch("board_ingest.ingest_ntfy", return_value=1) as ntfy:
                    self.assertEqual(poll_ordinary_issue_ntfy(), 1)
                ntfy.assert_called_once()
        finally:
            os.unlink(path)

    def test_slack_connector_issue_still_skips_ntfy(self) -> None:
        event = {
            "issue": {
                "number": 1,
                "title": "slack burst",
                "body": "carrier: slack-connector\ntext: hi",
            }
        }
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(event, fh)
            with mock.patch.dict(
                os.environ,
                {"GITHUB_EVENT_NAME": "issues", "GITHUB_EVENT_PATH": path},
                clear=False,
            ):
                self.assertTrue(skip_ntfy_on_slack_connector_issue(_read_for_test))
                with mock.patch("board_ingest.ingest_ntfy", side_effect=AssertionError("carrier poll")):
                    self.assertEqual(poll_ordinary_issue_ntfy(), 0)
        finally:
            os.unlink(path)

    def test_schedule_event_does_not_double_poll(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_EVENT_NAME": "schedule"}, clear=False):
            with mock.patch("board_ingest.ingest_ntfy", side_effect=AssertionError("double poll")):
                self.assertEqual(poll_ordinary_issue_ntfy(), 0)


def _read_for_test(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


if __name__ == "__main__":
    unittest.main()
