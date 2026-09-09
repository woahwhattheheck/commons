#!/usr/bin/env python3

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from upwork_capacity import compile_state, current_observation


EVENT_ID = "codex-upwork-marketplace-capacity-activation-20260902-01"
EVENT_SLACK_TS = "1788343601.055979"
EVENT_RECORD = "inventory/resources/records/" + EVENT_ID + ".json"


class TestUpworkMarketplaceResource(unittest.TestCase):
    def test_verified_email_is_reachable_not_submission(self):
        result = compile_state(current_observation())
        self.assertEqual(result["resource"], "upwork-marketplace-account")
        self.assertEqual(result["capacity"], "LIVE")
        self.assertEqual(result["stage"], "REACHABLE")
        self.assertEqual(result["condition"], "CONSTRAINED")
        self.assertEqual(result["route"], "OWNER_PROFILE_STATE_REQUIRED")
        self.assertFalse(result["proposal_send_authorized"])
        self.assertEqual(result["proposal_receipts"], 0)
        self.assertEqual(result["revenue_usd"], 0)

    def test_private_account_fields_fail_closed(self):
        observation = current_observation()
        observation["email"] = "not-persisted@example.invalid"
        with self.assertRaisesRegex(ValueError, "private account fields"):
            compile_state(observation)

    def test_profile_complete_only_advances_to_assigned(self):
        observation = current_observation()
        observation["profile_state"] = "COMPLETE"
        result = compile_state(observation)
        self.assertEqual(result["stage"], "ASSIGNED")
        self.assertEqual(result["route"], "PROPOSAL_PREFLIGHT_READY")
        self.assertFalse(result["proposal_send_authorized"])

    def test_ledger_and_activation_are_exact(self):
        with open(os.path.join(ROOT, "ground", "RESOURCE_LEDGER.json"), encoding="utf-8") as handle:
            ledger = json.load(handle)
        rows = [row for row in ledger["surfaces"] if row["name"] == "upwork-marketplace-account"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["stage"], "REACHABLE")
        self.assertEqual(rows[0]["condition"], "CONSTRAINED")
        self.assertIn("OWNER_ONLY", rows[0]["authority"])
        self.assertEqual(rows[0]["last_receipt"], EVENT_ID)
        chain = [ledger.get("source_id"), *(ledger.get("supersedes_source_ids") or [])]
        self.assertIn(EVENT_ID, chain)
        self.assertIn(EVENT_RECORD, ledger.get("record_sources") or [])

        path = os.path.join(ROOT, "inventory", "resources", "records", EVENT_ID + ".json")
        with open(path, encoding="utf-8") as handle:
            activation = json.load(handle)
        self.assertEqual(activation["selected_resource"], "upwork-marketplace-account")
        self.assertEqual(activation["projection"]["resources"], 71)
        self.assertEqual(activation["projection"]["producing"], 44)
        self.assertEqual(activation["account_truth"]["proposal_receipts"], 0)
        self.assertEqual(activation["next_watermark"]["commons_slack_ts"], EVENT_SLACK_TS)
        text = json.dumps(activation).lower()
        for forbidden in ("password", "recovery_link", "cookie", "oauth_token"):
            self.assertNotIn(forbidden, text)

    def test_later_ledger_header_cannot_erase_upwork_surface(self):
        with open(os.path.join(ROOT, "ground", "RESOURCE_LEDGER.json"), encoding="utf-8") as handle:
            ledger = json.load(handle)
        rows = [row for row in ledger["surfaces"] if row["name"] == "upwork-marketplace-account"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["last_receipt"], EVENT_ID)
        if ledger.get("source_id") != EVENT_ID:
            self.assertIn(EVENT_ID, ledger.get("supersedes_source_ids") or [])
            self.assertNotEqual(ledger.get("slack_ts"), EVENT_SLACK_TS)


if __name__ == "__main__":
    unittest.main()
