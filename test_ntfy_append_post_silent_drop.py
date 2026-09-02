"""FLINT MEASURED: ntfy 200 + ACCEPTED_DURABILITY_PENDING is not a p/ page.

Spark FastSubmit used to return ACCEPTED after ntfy HTTP 200 even when the
packed envelope was over NTFY_MAX. Ingest then records INGEST_ERROR
unparseable-or-oversize and never writes p/{id}.md. Law: ntfy 200 is not a post.

The live event 2EiiAnFpfde5 was under cap. The silent drop was issue ingest
skipping ntfy entirely. Ordinary issue runs must poll ntfy; Slack-connector
bursts still skip.

Do not remint Contents-API receipt 07fa3bee / fable-puzzle71-organs-fold-tick.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest import mock

import commons_mcp as cm
from api import mcp
from host.ntfy_issue_poll import skip_ntfy_on_slack_connector_issue


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


class SlackConnectorSkipIsNarrow(unittest.TestCase):
    def test_ordinary_issues_event_still_polls_ntfy(self) -> None:
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
                self.assertFalse(skip_ntfy_on_slack_connector_issue(board_ingest._read))
                with mock.patch.object(board_ingest, "ingest_ntfy", return_value=1) as ntfy, \
                     mock.patch.object(board_ingest, "ingest_github_event", return_value=0), \
                     mock.patch.object(board_ingest, "sweep_collect", return_value=[]), \
                     mock.patch.object(board_ingest, "rebuild"), \
                     mock.patch.object(board_ingest, "list_posts", return_value=[]), \
                     mock.patch.object(
                         board_ingest, "materialize_pending_grok_com_jobs", return_value=[]
                     ):
                    self.assertEqual(board_ingest._ingest_and_maybe_publish(False), 0)
                ntfy.assert_called_once()
        finally:
            os.unlink(path)

    def test_slack_connector_issue_still_skips_ntfy(self) -> None:
        import board_ingest

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
                self.assertTrue(skip_ntfy_on_slack_connector_issue(board_ingest._read))
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
