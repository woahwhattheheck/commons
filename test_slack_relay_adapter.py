#!/usr/bin/env python3
"""Focused contract tests for the Slack destination adapter."""

from __future__ import annotations

import io
import json
import unittest
from pathlib import Path
from unittest import mock

import ntfy_relays
from integrations.grok_slack.bridge import credential_presence as grok_credential_presence
from host import slack_relay_adapter


ROOT = Path(__file__).resolve().parent
SECRET = "xoxb-DO-NOT-WRITE-THIS-TOKEN-INTO-GIT-OR-RECEIPTS"
APP_SECRET = "xapp-DO-NOT-WRITE-THIS-APP-TOKEN-EITHER"

OFFER = {
    "id": "caliper-slack-relay-fixture-01",
    "body": "discord journal row for slack dest",
    "source_host": "local-uncredentialed-bridge",
    "channel": "C0BRGMDQB6G",
}


def _calls_urlopen(*_args, **_kwargs):
    raise AssertionError("adapter opened a network socket")


class SlackRelayAdapterTests(unittest.TestCase):
    def test_test_mode_synthetic_receipt_is_byte_identical_and_sends_nothing(self) -> None:
        stamp = "2026-09-01T10:00:00Z"
        with mock.patch.object(ntfy_relays, "replay") as replay, mock.patch(
            "urllib.request.urlopen", side_effect=_calls_urlopen
        ):
            first = slack_relay_adapter.canonical(
                slack_relay_adapter.deliver(OFFER, mode="test", env={}, observed_at=stamp)
            )
            second = slack_relay_adapter.canonical(
                slack_relay_adapter.deliver(OFFER, mode="test", env={}, observed_at=stamp)
            )
        self.assertEqual(first, second)
        replay.assert_not_called()
        receipt = json.loads(first)
        self.assertEqual(receipt["schema"], slack_relay_adapter.SCHEMA)
        self.assertEqual(receipt["state"], "SYNTHETIC_DELIVERED")
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["mode"], "test")
        self.assertEqual(receipt["network_calls"], 0)
        self.assertFalse(receipt["real_slack_send"])
        self.assertFalse(receipt["silent_skip"])
        self.assertEqual(receipt["envelope"]["id"], OFFER["id"])
        self.assertEqual(receipt["reused"], list(slack_relay_adapter.REUSED))

    def test_credential_absence_fails_closed_with_explicit_receipt(self) -> None:
        transport = mock.Mock(side_effect=AssertionError("transport must not run"))
        receipt = slack_relay_adapter.deliver(
            OFFER, mode="live", env={}, transport=transport, observed_at="2026-09-01T10:00:00Z"
        )
        transport.assert_not_called()
        self.assertFalse(receipt["ok"])
        self.assertEqual(receipt["state"], "CREDENTIAL_ABSENT")
        self.assertTrue(receipt["credentials_missing"])
        self.assertEqual(receipt["credential_presence"]["SLACK_BOT_TOKEN"], "missing")
        self.assertEqual(receipt["credential_presence"]["SLACK_APP_TOKEN"], "missing")
        self.assertEqual(
            receipt["credential_sources"]["gemini_slack"]["SLACK_BOT_TOKEN"], "missing"
        )
        self.assertFalse(receipt["silent_skip"])
        self.assertFalse(receipt["real_slack_send"])
        self.assertEqual(receipt["network_calls"], 0)
        self.assertIn("Fail closed", receipt["note"])
        self.assertIn("Not a silent skip", receipt["note"])

    def test_live_with_credentials_refuses_real_slack_without_injected_transport(self) -> None:
        env = {"SLACK_BOT_TOKEN": SECRET, "SLACK_APP_TOKEN": APP_SECRET}
        with mock.patch.object(ntfy_relays, "replay") as replay:
            receipt = slack_relay_adapter.deliver(OFFER, mode="live", env=env)
        replay.assert_not_called()
        self.assertFalse(receipt["ok"])
        self.assertEqual(receipt["state"], "TRANSPORT_NOT_INJECTED")
        self.assertFalse(receipt["credentials_missing"])
        self.assertFalse(receipt["real_slack_send"])
        self.assertFalse(receipt["silent_skip"])
        blob = json.dumps(receipt)
        self.assertNotIn(SECRET, blob)
        self.assertNotIn(APP_SECRET, blob)
        self.assertNotIn("xoxb-", blob)
        self.assertNotIn("xapp-", blob)

    def test_test_mode_ignores_injected_transport_and_never_sends(self) -> None:
        transport = mock.Mock(return_value={"ok": True, "state": "SHOULD_NOT_RUN"})
        env = {"SLACK_BOT_TOKEN": SECRET, "SLACK_APP_TOKEN": APP_SECRET}
        receipt = slack_relay_adapter.deliver(
            OFFER, mode="test", env=env, transport=transport, observed_at="2026-09-01T10:00:00Z"
        )
        transport.assert_not_called()
        self.assertEqual(receipt["state"], "SYNTHETIC_DELIVERED")
        self.assertEqual(receipt["network_calls"], 0)
        self.assertFalse(receipt["real_slack_send"])
        self.assertNotIn(SECRET, json.dumps(receipt))

    def test_id_mismatch_fails_closed_before_any_transport(self) -> None:
        transport = mock.Mock(side_effect=AssertionError("transport must not run"))
        bad = {
            "id": "offer-a",
            "payload": {"id": "offer-b", "body": "mismatch"},
            "source_host": "local-uncredentialed-bridge",
        }
        with mock.patch.object(ntfy_relays, "replay") as replay:
            with self.assertRaises(slack_relay_adapter.RelayAdapterError):
                slack_relay_adapter.deliver(bad, mode="live", env={}, transport=transport)
        transport.assert_not_called()
        replay.assert_not_called()

    def test_unknown_mode_fails_closed(self) -> None:
        with self.assertRaisesRegex(slack_relay_adapter.RelayAdapterError, "unknown mode"):
            slack_relay_adapter.deliver(OFFER, mode="prod", env={})

    def test_wires_existing_relay_and_grok_presence_without_remint(self) -> None:
        self.assertIs(slack_relay_adapter.credential_presence, grok_credential_presence)
        self.assertIs(slack_relay_adapter.ntfy_relays, ntfy_relays)
        for rel in slack_relay_adapter.REUSED:
            self.assertTrue((ROOT / rel).is_file(), rel)
        with mock.patch.object(ntfy_relays, "relay_message", wraps=ntfy_relays.relay_message) as relay:
            slack_relay_adapter.deliver(OFFER, mode="test", env={}, observed_at="2026-09-01T10:00:00Z")
        relay.assert_called_once()
        event = relay.call_args.args[0]
        self.assertEqual(event["id"], OFFER["id"])
        self.assertEqual(event["payload"]["id"], OFFER["id"])

    def test_injected_transport_is_the_only_live_send_path(self) -> None:
        env = {"SLACK_BOT_TOKEN": "present-marker", "SLACK_APP_TOKEN": "present-marker"}
        seen = {}

        def transport(payload):
            seen.update(payload)
            return {"ok": True, "state": "INJECTED_OK"}

        receipt = slack_relay_adapter.deliver(
            OFFER, mode="live", env=env, transport=transport, observed_at="2026-09-01T10:00:00Z"
        )
        self.assertEqual(receipt["state"], "INJECTED_OK")
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["network_calls"], 1)
        self.assertFalse(receipt["real_slack_send"])
        self.assertEqual(seen["offer_id"], OFFER["id"])
        self.assertEqual(seen["envelope"]["id"], OFFER["id"])
        self.assertNotIn("present-marker", json.dumps(receipt))

    def test_self_test_and_cli_pass(self) -> None:
        report = slack_relay_adapter.self_test()
        self.assertEqual(report["status"], "PASS")
        stdout = io.BytesIO()
        with mock.patch.object(slack_relay_adapter.sys, "stdout", stdout):
            code = slack_relay_adapter.main(["--self-test"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
