from __future__ import annotations

import copy
import unittest

from coordination.connector_preflight import compile_at
from coordination.connector_preflight.test_preflight import SHA_C, T0, attempt, base_input


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


if __name__ == "__main__":
    unittest.main()
