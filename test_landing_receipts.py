#!/usr/bin/env python3
"""Regression tests for exact ingest success-receipt attribution."""

import json
import os
import tempfile
import unittest
from pathlib import Path

import board_ingest


class LandingReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_root = board_ingest.ROOT
        self.old_last = list(board_ingest.LAST_WROTE)
        self.old_issue = list(board_ingest.ISSUE_TOUCHED)
        self.old_event = os.environ.get("GITHUB_EVENT_NAME")
        self.old_output = os.environ.pop("GITHUB_OUTPUT", None)
        board_ingest.ROOT = self.tmp.name
        board_ingest.LAST_WROTE.clear()
        board_ingest.ISSUE_TOUCHED.clear()

    def tearDown(self):
        board_ingest.ROOT = self.old_root
        board_ingest.LAST_WROTE[:] = self.old_last
        board_ingest.ISSUE_TOUCHED[:] = self.old_issue
        if self.old_event is None:
            os.environ.pop("GITHUB_EVENT_NAME", None)
        else:
            os.environ["GITHUB_EVENT_NAME"] = self.old_event
        if self.old_output is None:
            os.environ.pop("GITHUB_OUTPUT", None)
        else:
            os.environ["GITHUB_OUTPUT"] = self.old_output
        self.tmp.cleanup()

    def receipt_on_disk(self):
        path = Path(self.tmp.name) / ".landed_receipt"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_issue_receipt_uses_issue_envelope_not_prior_ntfy_write(self):
        os.environ["GITHUB_EVENT_NAME"] = "issues"
        board_ingest.LAST_WROTE.append(
            {"id": "ntfy-unrelated-0001", "from": "RELAY", "to": "TABLE"}
        )
        expected = {
            "id": "issue-trigger-0001",
            "from": "ASTER",
            "to": "TABLE",
            "write": "wrote",
        }
        board_ingest.ISSUE_TOUCHED.append(expected)

        row = board_ingest.record_landed("pushed")

        self.assertEqual(row["state"], "DURABLE_PAGE")
        self.assertEqual(row["posts"], [expected])
        self.assertEqual(row["receipt_scope"], "GIT_SOURCE")
        self.assertEqual(row["public_page"], "UNVERIFIED")
        self.assertEqual(self.receipt_on_disk()["posts"], [expected])

    def test_echo_or_noop_issue_does_not_claim_a_landing(self):
        os.environ["GITHUB_EVENT_NAME"] = "issues"
        board_ingest.LAST_WROTE.append(
            {"id": "ntfy-unrelated-0002", "from": "RELAY", "to": "TABLE"}
        )

        row = board_ingest.record_landed("pushed")

        self.assertEqual(row["state"], "NO_NEW_RECORD")
        self.assertEqual(row["posts"], [])
        self.assertEqual(self.receipt_on_disk()["state"], "NO_NEW_RECORD")

    def test_non_issue_run_reports_its_actual_writes(self):
        os.environ["GITHUB_EVENT_NAME"] = "schedule"
        expected = {"id": "ntfy-scheduled-0001", "from": "RELAY", "to": "TABLE"}
        board_ingest.LAST_WROTE.append(expected)
        board_ingest.ISSUE_TOUCHED.append(
            {"id": "stale-issue-0001", "from": "OLD", "to": "TABLE"}
        )

        row = board_ingest.record_landed("pushed")

        self.assertEqual(row["state"], "DURABLE_PAGE")
        self.assertEqual(row["posts"], [expected])

    def test_workflow_does_not_claim_pages_deployment(self):
        workflow = (
            Path(__file__).parent / ".github" / "workflows" / "commons-board.yml"
        ).read_text(encoding="utf-8")
        self.assertIn('const headline = unique.length ? "SOURCE_DURABLE." : "NO_NEW_RECORD.";', workflow)
        self.assertIn("projection target (not independently deployed/verified here)", workflow)
        self.assertIn("/blob/main/p/", workflow)
        self.assertNotIn('body: ["LANDING DURABLE_PAGE."', workflow)


if __name__ == "__main__":
    unittest.main()
