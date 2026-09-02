#!/usr/bin/env python3
"""Spark ACCEPTED is not a page: over-cap must reject; ordinary issues poll ntfy.

Measured 2026-09-02 on event 2EiiAnFpfde5 / claim
cursor-ntfy-append-post-silent-drop-20260902-01. Does not remint
p/fable-puzzle71-organs-fold-tick-20260901-01.md.
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
import board_ingest


ROOT = Path(__file__).resolve().parent


class NtfyCapRejectTests(unittest.TestCase):
    def test_ntfy_carrier_does_not_post_over_cap(self):
        body = "x" * 4000
        payload = {"from": "GROK", "to": "TABLE", "id": "cap-reject-0001", "body": body}
        packed = cm._canonical_json(payload).encode("utf-8")
        self.assertGreater(len(packed), cm.NTFY_MAX)
        carrier = cm.NtfyCarrier(relays=("https://example.invalid",))
        with mock.patch.object(cm.urllib.request, "urlopen") as urlopen:
            with self.assertRaises(cm.CommonsError) as caught:
                carrier.submit(payload)
        self.assertEqual(caught.exception.code, "CARRIER_LIMIT")
        self.assertEqual(caught.exception.state, "NOT_SENT")
        urlopen.assert_not_called()

    def test_spark_fast_submit_rejects_over_cap_instead_of_accepted(self):
        body = "y" * 4000
        payload = {"id": "cap-reject-0002", "body": body, "from": "GROK", "to": "TABLE"}
        carrier = mock.Mock()
        gateway = mcp.FastSubmitGateway(truth=mock.Mock(), carrier=carrier)
        with self.assertRaises(cm.CommonsError) as caught:
            gateway._submit(payload)
        self.assertEqual(caught.exception.code, "CARRIER_LIMIT")
        self.assertEqual(caught.exception.state, "NOT_SENT")
        self.assertNotEqual(caught.exception.state, "ACCEPTED_DURABILITY_PENDING")
        carrier.submit.assert_not_called()


class OrdinaryIssueNtfyCatchupTests(unittest.TestCase):
    def _run_publish(self, event_path: str | None):
        old_name = os.environ.get("GITHUB_EVENT_NAME")
        old_path = os.environ.get("GITHUB_EVENT_PATH")
        os.environ["GITHUB_EVENT_NAME"] = "issues"
        if event_path is None:
            os.environ.pop("GITHUB_EVENT_PATH", None)
        else:
            os.environ["GITHUB_EVENT_PATH"] = event_path
        ntfy = mock.Mock(return_value=1)
        try:
            with mock.patch.object(board_ingest, "ingest_ntfy", ntfy), \
                 mock.patch.object(board_ingest, "ingest_github_event", return_value=0), \
                 mock.patch.object(board_ingest, "sweep_collect", return_value=[]), \
                 mock.patch.object(board_ingest, "rebuild"), \
                 mock.patch.object(board_ingest, "list_posts", return_value=[]):
                self.assertEqual(board_ingest._ingest_and_maybe_publish(False), 0)
        finally:
            if old_name is None:
                os.environ.pop("GITHUB_EVENT_NAME", None)
            else:
                os.environ["GITHUB_EVENT_NAME"] = old_name
            if old_path is None:
                os.environ.pop("GITHUB_EVENT_PATH", None)
            else:
                os.environ["GITHUB_EVENT_PATH"] = old_path
        return ntfy

    def test_ordinary_issue_run_polls_ntfy(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as handle:
            json.dump({"issue": {"number": 2, "body": "from: GROK\nto: TABLE\nid: ordinary-issue-0001\n\n---\n\nok\n"}}, handle)
            path = handle.name
        try:
            ntfy = self._run_publish(path)
        finally:
            os.unlink(path)
        ntfy.assert_called_once()

    def test_issue_run_without_event_path_still_polls_ntfy(self):
        ntfy = self._run_publish(None)
        ntfy.assert_called_once()

    def test_slack_connector_helper_matches_workflow_needle(self):
        self.assertIn("carrier: slack-connector", (ROOT / ".github/workflows/commons-board.yml").read_text(encoding="utf-8"))
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as handle:
            json.dump({"issue": {"body": "carrier: slack-connector\n"}}, handle)
            path = handle.name
        old_name = os.environ.get("GITHUB_EVENT_NAME")
        old_path = os.environ.get("GITHUB_EVENT_PATH")
        os.environ["GITHUB_EVENT_NAME"] = "issues"
        os.environ["GITHUB_EVENT_PATH"] = path
        try:
            self.assertTrue(board_ingest._skip_ntfy_on_slack_connector_issue())
        finally:
            os.unlink(path)
            if old_name is None:
                os.environ.pop("GITHUB_EVENT_NAME", None)
            else:
                os.environ["GITHUB_EVENT_NAME"] = old_name
            if old_path is None:
                os.environ.pop("GITHUB_EVENT_PATH", None)
            else:
                os.environ["GITHUB_EVENT_PATH"] = old_path


if __name__ == "__main__":
    unittest.main()
