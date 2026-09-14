from __future__ import annotations

import copy
import os
import tempfile
import unittest
from pathlib import Path

from coordination.connector_preflight import PreflightError, compile_at
from coordination.connector_preflight.latest import read_json_file
from coordination.connector_preflight.test_preflight import SHA_C, SHA_D, T0, attempt, base_input


class LatestDiscoveryTests(unittest.TestCase):
    def _second(self, raw):
        second = copy.deepcopy(raw["discoveries"][0])
        second["request_id"] = "discovery-002"
        second["requested_at"] = "2026-09-14T04:38:10Z"
        second["completed_at"] = "2026-09-14T04:38:15Z"
        second["evidence_sha256"] = SHA_C
        raw["discoveries"].append(second)
        return second

    def test_latest_complete_discovery_controls_catalog(self):
        raw = base_input()
        second = self._second(raw)
        second["actions"] = [
            {"connector": "GitHub", "name": "fetch_file", "access": "READ"},
            {"connector": "Slack", "name": "slack_read_channel", "access": "READ"},
        ]
        packet = compile_at(raw, T0)["packet"]
        self.assertEqual("BLOCKER_SUPPORTED", packet["overall_state"])
        self.assertTrue(packet["work_blocked_claim_supported"])

    def test_old_success_does_not_confirm_new_discovery(self):
        raw = base_input(attempts=[attempt("attempt-github-old", "GitHub", "create_branch", "SUCCESS")])
        self._second(raw)
        packet = compile_at(raw, T0)["packet"]
        github = next(row for row in packet["connectors"] if row["connector"] == "GitHub")
        self.assertEqual("WRITE_ATTEMPT_REQUIRED", github["state"])
        self.assertEqual("WRITE_ATTEMPT_REQUIRED", packet["overall_state"])

    def test_same_time_latest_catalog_conflict_holds(self):
        raw = base_input()
        second = copy.deepcopy(raw["discoveries"][0])
        second["request_id"] = "discovery-002"
        second["evidence_sha256"] = SHA_C
        second["actions"] = [
            {"connector": "GitHub", "name": "fetch_file", "access": "READ"},
            {"connector": "Slack", "name": "slack_read_channel", "access": "READ"},
        ]
        raw["discoveries"].append(second)
        packet = compile_at(raw, T0)["packet"]
        self.assertEqual("HOLD", packet["overall_state"])
        self.assertIn("LATEST_DISCOVERY_CATALOG_CONFLICT", packet["reasons"])

    def test_other_write_action_prevents_read_only_blocker(self):
        raw = base_input()
        raw["discoveries"][0]["actions"] = [
            {"connector": "GitHub", "name": "fetch_file", "access": "READ"},
            {"connector": "GitHub", "name": "create_issue", "access": "WRITE"},
            {"connector": "Slack", "name": "slack_read_channel", "access": "READ"},
        ]
        packet = compile_at(raw, T0)["packet"]
        github = next(row for row in packet["connectors"] if row["connector"] == "GitHub")
        self.assertEqual("WRITE_ATTEMPT_REQUIRED", github["state"])
        self.assertFalse(packet["work_blocked_claim_supported"])

    def test_successful_unlisted_write_confirms_rail(self):
        raw = base_input(
            attempts=[
                attempt("attempt-github-issue", "GitHub", "create_issue", "SUCCESS"),
                attempt("attempt-slack-send", "Slack", "slack_send_message", "SUCCESS", digest=SHA_D),
            ]
        )
        github_action = next(
            row for row in raw["discoveries"][0]["actions"] if row["name"] == "create_branch"
        )
        github_action["name"] = "create_issue"
        packet = compile_at(raw, T0)["packet"]
        self.assertEqual("WRITE_RAIL_CONFIRMED", packet["overall_state"])
        self.assertFalse(packet["work_blocked_claim_supported"])

    def test_unattempted_other_write_prevents_blocker(self):
        raw = base_input(
            attempts=[
                attempt("attempt-github-branch", "GitHub", "create_branch", "UNAVAILABLE"),
                attempt("attempt-slack-send", "Slack", "slack_send_message", "UNAVAILABLE", digest=SHA_D),
            ]
        )
        raw["discoveries"][0]["actions"].append(
            {"connector": "GitHub", "name": "create_issue", "access": "WRITE"}
        )
        packet = compile_at(raw, T0)["packet"]
        github = next(row for row in packet["connectors"] if row["connector"] == "GitHub")
        self.assertFalse(github["blocker_supported"])
        self.assertFalse(packet["work_blocked_claim_supported"])

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO unavailable")
    def test_fifo_input_rejected_without_waiting_for_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            fifo = Path(tmp) / "input.fifo"
            os.mkfifo(fifo)
            with self.assertRaisesRegex(PreflightError, "regular file"):
                read_json_file(fifo)


if __name__ == "__main__":
    unittest.main()
