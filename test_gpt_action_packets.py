#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from host import gpt_action_packets


ROOT = Path(__file__).resolve().parent


class GptActionPacketTests(unittest.TestCase):
    def test_packets_preserve_dnr_and_zero_cash(self) -> None:
        packets = json.loads((ROOT / "revenue" / "right_now" / "action_packets.json").read_text(encoding="utf-8"))
        self.assertEqual(packets["cash"]["collected_cash_usd"], 0)
        held = {row["candidate_id"]: row for row in packets["packets"]}
        self.assertEqual(held["metaforms"]["status"], "do-not-resend")
        self.assertEqual(held["anythingllm-mintplex"]["status"], "do-not-resend")
        self.assertIsNone(held["metaforms"]["concise_proposed_message"])
        self.assertNotIn("buy.stripe.com", json.dumps(packets))

    def test_experiments_are_eight_and_unpaid(self) -> None:
        experiments = json.loads((ROOT / "revenue" / "right_now" / "experiments.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(experiments["experiments"]), 8)
        self.assertEqual(experiments["collected_cash_usd"], 0)
        self.assertTrue(all("NOT_LANDED" in row["observed_result"] or row["observed_result"].startswith("NOT_LANDED") for row in experiments["experiments"]))

    def test_triage_is_free_and_local(self) -> None:
        page = (ROOT / "agent-triage.html").read_text(encoding="utf-8")
        script = (ROOT / "agent-triage.js").read_text(encoding="utf-8")
        self.assertIn("No login", page)
        self.assertIn("No telemetry", page)
        self.assertIn("generated_locally", script)
        self.assertIn("telemetry: false", script)
        self.assertNotIn("buy.stripe.com", page)
        right_now = (ROOT / "right-now.html").read_text(encoding="utf-8")
        self.assertIn("agent-triage.html", right_now)
        self.assertIn("ho-agent-failure-diagnostic", right_now)

    def test_ready_send_requires_live_first_party_receipt_and_confirm(self) -> None:
        packet = {
            "kind": "GPT_ACTION_PACKETS",
            "cash": {"collected_cash_usd": 0, "cash_claimed": False},
            "packets": [
                {
                    "candidate_id": "qualified-live",
                    "status": "ready-to-send under existing authorization",
                    "lane": "ready-to-send",
                    "economic_state_if_successful": "DISCOVERED",
                    "concise_proposed_message": "Bounded truthful message.",
                    "live_first_party_receipt": {
                        "state": "LIVE",
                        "evidence": "receipt://first-party/example",
                    },
                    "confirm_before_send": True,
                }
            ],
        }
        gpt_action_packets.validate_packets(packet)
        action = gpt_action_packets.next_external_action({}, packet)
        self.assertEqual(
            action,
            "confirm once, then send authorized packet qualified-live",
        )
        del packet["packets"][0]["live_first_party_receipt"]
        with self.assertRaises(gpt_action_packets.PacketError):
            gpt_action_packets.validate_packets(packet)

    def test_cli_validate_and_next(self) -> None:
        validate = subprocess.run(
            [sys.executable, str(ROOT / "host" / "gpt_action_packets.py"), "validate"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("USD 0 cash", validate.stdout)
        nxt = subprocess.run(
            [sys.executable, str(ROOT / "host" / "gpt_action_packets.py"), "next"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(nxt.stdout.strip(), "draft packet for composio without sending")


if __name__ == "__main__":
    unittest.main()
