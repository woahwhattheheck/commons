#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

from host import gpt_action_packets


ROOT = Path(__file__).resolve().parent
AUTH_NOW = datetime(2026, 9, 13, 10, 10, 0, tzinfo=timezone.utc)
AUTH_MESSAGE = "Bounded truthful message."
AUTH_ROUTE = "https://example.test/thread/1"


def _authorization(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "authorization_id": "auth-1",
        "generation": 1,
        "state": "LIVE",
        "candidate_id": "qualified-live",
        "contact_route": AUTH_ROUTE,
        "message_sha256": hashlib.sha256(AUTH_MESSAGE.encode("utf-8")).hexdigest(),
        "issued_at": "2026-09-13T10:00:00Z",
        "expires_at": "2026-09-13T10:20:00Z",
        "confirm_before_send": True,
        "evidence": ["receipt://first-party/example"],
    }
    row.update(overrides)
    return row


def _authorization_ledger(*rows: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": gpt_action_packets.AUTH_SCHEMA,
        "kind": gpt_action_packets.AUTH_KIND,
        "as_of": "2026-09-13T10:05:00Z",
        "authorizations": list(rows),
    }


def _ready_packet(
    *, receipt: dict[str, object] | None = None, **overrides: object
) -> dict[str, object]:
    row: dict[str, object] = {
        "candidate_id": "qualified-live",
        "status": "ready-to-send under existing authorization",
        "lane": "ready-to-send",
        "economic_state_if_successful": "DISCOVERED",
        "concise_proposed_message": AUTH_MESSAGE,
        "public_contact_route": AUTH_ROUTE,
        "live_first_party_receipt": receipt or _authorization(),
        "confirm_before_send": True,
    }
    row.update(overrides)
    return {
        "kind": "GPT_ACTION_PACKETS",
        "cash": {"collected_cash_usd": 0, "cash_claimed": False},
        "packets": [row],
    }


class GptActionPacketTests(unittest.TestCase):
    def test_packets_preserve_dnr_and_zero_cash(self) -> None:
        packets = json.loads(
            (ROOT / "revenue" / "right_now" / "action_packets.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(packets["cash"]["collected_cash_usd"], 0)
        held = {row["candidate_id"]: row for row in packets["packets"]}
        self.assertEqual(held["metaforms"]["status"], "do-not-resend")
        self.assertEqual(held["anythingllm-mintplex"]["status"], "do-not-resend")
        self.assertIsNone(held["metaforms"]["concise_proposed_message"])
        self.assertNotIn("buy.stripe.com", json.dumps(packets))

    def test_experiments_are_eight_and_unpaid(self) -> None:
        experiments = json.loads(
            (ROOT / "revenue" / "right_now" / "experiments.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertGreaterEqual(len(experiments["experiments"]), 8)
        self.assertEqual(experiments["collected_cash_usd"], 0)
        self.assertTrue(
            all(
                "NOT_LANDED" in row["observed_result"]
                or row["observed_result"].startswith("NOT_LANDED")
                for row in experiments["experiments"]
            )
        )

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

    def test_ready_send_requires_exact_current_bound_authorization(self) -> None:
        receipt = _authorization()
        authorizations = _authorization_ledger(receipt)
        packet = _ready_packet(receipt=copy.deepcopy(receipt))
        gpt_action_packets.validate_packets(
            packet, authorizations, evaluated_at=AUTH_NOW
        )
        action = gpt_action_packets.next_external_action(
            {}, packet, authorizations, evaluated_at=AUTH_NOW
        )
        self.assertEqual(
            action,
            "confirm once, then send authorized packet qualified-live",
        )

    def test_ready_send_rejects_cross_packet_and_receipt_replay(self) -> None:
        receipt = _authorization()
        authorizations = _authorization_ledger(receipt)
        hostile_packets = [
            _ready_packet(candidate_id="different-candidate"),
            _ready_packet(public_contact_route="https://example.test/thread/2"),
            _ready_packet(concise_proposed_message="Changed message."),
            _ready_packet(confirm_before_send=False),
            _ready_packet(lane="ready-to-draft"),
            _ready_packet(receipt={**receipt, "evidence": ["receipt://other"]}),
        ]
        for hostile in hostile_packets:
            with self.subTest(hostile=hostile["packets"][0]):
                with self.assertRaises(gpt_action_packets.PacketError):
                    gpt_action_packets.validate_packets(
                        hostile, authorizations, evaluated_at=AUTH_NOW
                    )

    def test_ready_send_rejects_missing_stale_future_and_revoked_authority(self) -> None:
        receipt = _authorization()
        packet = _ready_packet(receipt=copy.deepcopy(receipt))
        with self.assertRaises(gpt_action_packets.PacketError):
            gpt_action_packets.validate_packets(
                packet, _authorization_ledger(), evaluated_at=AUTH_NOW
            )
        with self.assertRaises(gpt_action_packets.PacketError):
            gpt_action_packets.validate_packets(
                packet,
                _authorization_ledger(receipt),
                evaluated_at=datetime(2026, 9, 13, 10, 20, tzinfo=timezone.utc),
            )
        with self.assertRaises(gpt_action_packets.PacketError):
            gpt_action_packets.validate_packets(
                packet,
                _authorization_ledger(receipt),
                evaluated_at=datetime(2026, 9, 13, 9, 59, 59, tzinfo=timezone.utc),
            )
        revoked = _authorization(
            authorization_id="auth-2", generation=2, state="REVOKED"
        )
        with self.assertRaises(gpt_action_packets.PacketError):
            gpt_action_packets.validate_packets(
                packet,
                _authorization_ledger(receipt, revoked),
                evaluated_at=AUTH_NOW,
            )

    def test_authorization_ledger_is_strict_and_bool_safe(self) -> None:
        hostile_ledgers = [
            _authorization_ledger(_authorization(generation=True)),
            _authorization_ledger(
                _authorization(), _authorization(authorization_id="auth-2")
            ),
            {
                **_authorization_ledger(_authorization()),
                "unexpected": "field",
            },
            _authorization_ledger(
                {**_authorization(), "unexpected": "field"}
            ),
        ]
        for hostile in hostile_ledgers:
            with self.subTest(hostile=hostile):
                with self.assertRaises(gpt_action_packets.PacketError):
                    gpt_action_packets.validate_packets(
                        _ready_packet(), hostile, evaluated_at=AUTH_NOW
                    )

    def test_next_revalidates_authority_at_consumption_boundary(self) -> None:
        receipt = _authorization()
        packet = _ready_packet(receipt=copy.deepcopy(receipt))
        authorizations = _authorization_ledger(receipt)
        self.assertEqual(
            gpt_action_packets.next_external_action(
                {}, packet, authorizations, evaluated_at=AUTH_NOW
            ),
            "confirm once, then send authorized packet qualified-live",
        )
        packet["packets"][0]["concise_proposed_message"] = "Moved after validation."
        with self.assertRaises(gpt_action_packets.PacketError):
            gpt_action_packets.next_external_action(
                {}, packet, authorizations, evaluated_at=AUTH_NOW
            )

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
        self.assertEqual(
            nxt.stdout.strip(),
            "Keep inbound doors live (agent-triage.html, agent-rescue.html, "
            "tokenjunkielabs@gmail.com). Do not resend held prospects. "
            "Founder still must evidence a chargeable processor path.",
        )


if __name__ == "__main__":
    unittest.main()
