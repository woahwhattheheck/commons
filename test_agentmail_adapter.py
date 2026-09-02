from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("agentmail", ROOT / "host" / "agentmail_adapter.py")
assert SPEC and SPEC.loader
agentmail = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agentmail)
NOW = "2026-09-02T01:30:00Z"


def unavailable() -> dict:
    return {
        "build_order_id": agentmail.ORDER,
        "observed_at": NOW,
        "agentmail_connector_state": "UNAVAILABLE",
        "gmail_fallback_state": "UNAVAILABLE",
        "inbox": {"state": "NOT_ATTEMPTED", "occurred_at": None, "provider_inbox_id": None},
        "outbound": {
            "state": "NOT_ATTEMPTED", "occurred_at": None,
            "provider_message_id": None, "payload_sha256": None,
        },
        "inbound": {
            "state": "NOT_ATTEMPTED", "occurred_at": None,
            "provider_message_id": None, "payload_sha256": None,
        },
    }


class AgentMailAdapterTests(unittest.TestCase):
    def test_checked_in_unavailable_receipt_is_canonical_and_zero_send(self) -> None:
        path = ROOT / "revenue" / "swarm_mail" / "agentmail_first_inbox_receipt.json"
        receipt = json.loads(path.read_text(encoding="utf-8"))
        agentmail.validate_public_receipt(receipt)
        self.assertEqual(receipt, agentmail.project_receipt({
            **unavailable(), "observed_at": receipt["observed_at"],
        }))
        self.assertEqual(receipt["terminal_state"], "ROAD_UNAVAILABLE")
        self.assertEqual(receipt["policy"]["send_attempts"], 0)
        self.assertFalse(receipt["policy"]["resend_permitted"])
        self.assertFalse(receipt["policy"]["external_prospect_contact"])

    def test_complete_provider_observation_proves_round_trip(self) -> None:
        observation = unavailable()
        observation.update({
            "agentmail_connector_state": "AVAILABLE",
            "gmail_fallback_state": "NOT_NEEDED",
            "inbox": {
                "state": "CREATED", "occurred_at": NOW,
                "provider_inbox_id": "inbox_01JTEST",
            },
            "outbound": {
                "state": "PROVIDER_ACCEPTED", "occurred_at": NOW,
                "provider_message_id": "msg_out_01JTEST", "payload_sha256": "sha256:" + "1" * 64,
            },
            "inbound": {
                "state": "PROVIDER_OBSERVED", "occurred_at": NOW,
                "provider_message_id": "msg_in_01JTEST", "payload_sha256": "sha256:" + "2" * 64,
            },
        })
        receipt = agentmail.project_receipt(observation)
        agentmail.validate_public_receipt(receipt)
        self.assertEqual(receipt["terminal_state"], "ROUND_TRIP_PROVEN")
        self.assertEqual(receipt["policy"]["send_attempts"], 1)
        self.assertTrue(all(receipt["proof"].values()))
        self.assertNotIn("@", json.dumps(receipt))

    def test_private_fields_and_reminted_order_are_rejected(self) -> None:
        for field in ("recipient", "subject", "body", "headers", "oauth_token"):
            observation = unavailable()
            observation[field] = "private"
            with self.subTest(field=field), self.assertRaises(agentmail.AgentMailReceiptError):
                agentmail.project_receipt(observation)
        observation = unavailable()
        observation["build_order_id"] = "rival-order"
        with self.assertRaises(agentmail.AgentMailReceiptError):
            agentmail.project_receipt(observation)

    def test_unavailable_connector_cannot_claim_operations(self) -> None:
        observation = unavailable()
        observation["inbox"] = {
            "state": "CREATED", "occurred_at": NOW,
            "provider_inbox_id": "inbox_without_road",
        }
        with self.assertRaises(agentmail.AgentMailReceiptError):
            agentmail.project_receipt(observation)

    def test_validator_rejects_contradictory_proof_or_policy(self) -> None:
        receipt = agentmail.project_receipt(unavailable())
        for path, value in (
            (("proof", "round_trip_proven"), True),
            (("policy", "resend_permitted"), True),
        ):
            changed = copy.deepcopy(receipt)
            changed[path[0]][path[1]] = value
            with self.subTest(path=path), self.assertRaises(agentmail.AgentMailReceiptError):
                agentmail.validate_public_receipt(changed)

    def test_cli_does_not_echo_rejected_private_content(self) -> None:
        observation = unavailable()
        observation["body"] = "DO-NOT-ECHO-PRIVATE-CONTENT"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "observation.json"
            path.write_text(json.dumps(observation), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "host" / "agentmail_adapter.py"), str(path)],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("DO-NOT-ECHO-PRIVATE-CONTENT", result.stdout)
        self.assertEqual(json.loads(result.stdout)["state"], "RECEIPT_REJECTED")


if __name__ == "__main__":
    unittest.main()
