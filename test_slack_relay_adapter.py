#!/usr/bin/env python3
"""Focused contract tests for the synthetic/read-only Slack destination adapter."""
from __future__ import annotations

import io
import json
import unittest
from pathlib import Path
from unittest import mock

from host import slack_relay_adapter as adapter


ROOT = Path(__file__).resolve().parent
WIRED = (
    ROOT / "ntfy_relays.py",
    ROOT / "integrations" / "grok_slack" / "bridge.py",
    ROOT / "integrations" / "gemini_slack" / "bridge.py",
)
PRESENT_ENV = {
    "SLACK_BOT_TOKEN": "test-bot-present",
    "SLACK_APP_TOKEN": "test-app-present",
}


def event(**overrides):
    row = {
        "id": "caliper-slack-relay-adapter-01",
        "text": "synthetic Slack destination ping",
        "source_host": "local-uncredentialed",
        "carrier_origin": "discord-direct-root",
        "channel": "C0BRGMDQB6G",
    }
    row.update(overrides)
    return row


class SlackRelayAdapterTests(unittest.TestCase):
    def test_test_mode_receipt_is_byte_identical_twice(self) -> None:
        first = json.dumps(
            adapter.deliver(event(), mode="test", env={}, now="2026-09-01T00:00:00Z"),
            sort_keys=True,
            separators=(",", ":"),
        )
        second = json.dumps(
            adapter.deliver(event(), mode="test", env={}, now="2026-09-01T00:00:00Z"),
            sort_keys=True,
            separators=(",", ":"),
        )
        self.assertEqual(first, second)

    def test_test_mode_delivers_synthetic_receipt_end_to_end(self) -> None:
        transport = mock.Mock(side_effect=AssertionError("transport must not run"))
        with mock.patch("urllib.request.urlopen") as urlopen:
            receipt = adapter.deliver(
                event(),
                mode="test",
                env={},
                transport=transport,
                now="2026-09-01T00:00:00Z",
            )
        urlopen.assert_not_called()
        transport.assert_not_called()
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["state"], adapter.SYNTHETIC_STATE)
        self.assertEqual(receipt["schema"], adapter.RECEIPT_SCHEMA)
        self.assertEqual(receipt["adapter"], "host/slack_relay_adapter.py")
        self.assertEqual(receipt["mode"], "test")
        self.assertTrue(receipt["read_only"])
        self.assertTrue(receipt["synthetic"])
        self.assertFalse(receipt["admission_gate"])
        self.assertFalse(receipt["credential_gate"])
        self.assertFalse(receipt["real_send"])
        self.assertFalse(receipt["silent_skip"])
        self.assertFalse(receipt["fail_closed"])
        self.assertEqual(receipt["network_calls"], 0)
        self.assertTrue(receipt["slack_ts"].startswith("synthetic."))
        self.assertEqual(receipt["id"], "caliper-slack-relay-adapter-01")
        self.assertEqual(receipt["source_host"], "local-uncredentialed")
        self.assertEqual(receipt["carrier_origin"], "discord-direct-root")
        self.assertEqual(receipt["wired"], list(adapter.WIRED_PATHS))
        self.assertEqual(
            receipt["credential_presence"],
            {"SLACK_BOT_TOKEN": "missing", "SLACK_APP_TOKEN": "missing"},
        )

    def test_credentials_present_are_overlay_only_and_never_send(self) -> None:
        transport = mock.Mock(return_value={"ok": True, "ts": "should-not-run"})
        with mock.patch("urllib.request.urlopen") as urlopen:
            receipt = adapter.deliver(event(), mode="test", env=PRESENT_ENV, transport=transport)
        urlopen.assert_not_called()
        transport.assert_not_called()
        self.assertEqual(receipt["state"], adapter.SYNTHETIC_STATE)
        self.assertTrue(receipt["ok"])
        self.assertTrue(receipt["read_only"])
        self.assertFalse(receipt["admission_gate"])
        self.assertFalse(receipt["real_send"])
        self.assertEqual(receipt["network_calls"], 0)
        self.assertEqual(
            receipt["credential_presence"],
            {"SLACK_BOT_TOKEN": "present", "SLACK_APP_TOKEN": "present"},
        )
        blob = json.dumps(receipt)
        self.assertNotIn("test-bot-present", blob)
        self.assertNotIn("test-app-present", blob)
        self.assertNotIn("xoxb-", blob)
        self.assertNotIn("xapp-", blob)

    def test_live_mode_missing_credentials_is_synthetic_not_an_admission_gate(self) -> None:
        transport = mock.Mock(side_effect=AssertionError("must not send when uncredentialed"))
        with mock.patch("urllib.request.urlopen") as urlopen:
            receipt = adapter.deliver(event(), mode="live", env={}, transport=transport)
        urlopen.assert_not_called()
        transport.assert_not_called()
        self.assertIsInstance(receipt, dict)
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["state"], adapter.SYNTHETIC_STATE)
        self.assertEqual(receipt["mode"], "live")
        self.assertTrue(receipt["read_only"])
        self.assertTrue(receipt["synthetic"])
        self.assertFalse(receipt["admission_gate"])
        self.assertFalse(receipt["credential_gate"])
        self.assertFalse(receipt["fail_closed"])
        self.assertFalse(receipt["silent_skip"])
        self.assertFalse(receipt["real_send"])
        self.assertEqual(receipt["network_calls"], 0)
        self.assertTrue(receipt["slack_ts"].startswith("synthetic."))
        self.assertIn("not an admission gate", receipt["reason"])
        self.assertEqual(
            receipt["missing_credentials"],
            ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN"],
        )

    def test_blank_tokens_are_overlay_missing_and_still_synthetic(self) -> None:
        env = {"SLACK_BOT_TOKEN": "  ", "SLACK_APP_TOKEN": ""}
        receipt = adapter.deliver(event(), mode="live", env=env)
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["state"], adapter.SYNTHETIC_STATE)
        self.assertFalse(receipt["admission_gate"])
        self.assertFalse(receipt["fail_closed"])
        self.assertFalse(receipt["silent_skip"])
        self.assertEqual(
            receipt["credential_presence"],
            {"SLACK_BOT_TOKEN": "missing", "SLACK_APP_TOKEN": "missing"},
        )

    def test_live_mode_with_credentials_never_invokes_transport(self) -> None:
        transport = mock.Mock(return_value={"ok": True, "ts": "1788300000.000001"})
        with mock.patch("urllib.request.urlopen") as urlopen:
            receipt = adapter.deliver(event(), mode="live", env=PRESENT_ENV, transport=transport)
        urlopen.assert_not_called()
        transport.assert_not_called()
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["state"], adapter.SYNTHETIC_STATE)
        self.assertTrue(receipt["read_only"])
        self.assertFalse(receipt["admission_gate"])
        self.assertFalse(receipt["real_send"])
        self.assertEqual(receipt["network_calls"], 0)
        self.assertTrue(receipt["slack_ts"].startswith("synthetic."))
        self.assertNotEqual(receipt["slack_ts"], "1788300000.000001")

    def test_ntfy_shaped_event_preserves_origin_and_refuses_id_rewrite(self) -> None:
        ntfy_event = {
            "id": "caller-stable-id",
            "payload": {"id": "caller-stable-id", "body": "same body"},
            "host": "https://relay.example/",
            "source_host": "https://relay.example/",
            "carrier_origin": "https://first.example/",
        }
        receipt = adapter.deliver(ntfy_event, mode="test", env={})
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["source_host"], "https://relay.example")
        self.assertEqual(receipt["carrier_origin"], "https://first.example")
        composed = adapter.normalize_event(ntfy_event)
        payload = json.loads(composed["text"])
        self.assertEqual(payload["id"], "caller-stable-id")
        self.assertEqual(payload["body"], "same body")

        mismatch = dict(ntfy_event)
        mismatch["id"] = "different-id"
        closed = adapter.deliver(mismatch, mode="test", env={})
        self.assertFalse(closed["ok"])
        self.assertEqual(closed["state"], adapter.INVALID_EVENT_STATE)
        self.assertTrue(closed["fail_closed"])
        self.assertFalse(closed["admission_gate"])
        self.assertFalse(closed["silent_skip"])

    def test_unknown_mode_and_empty_event_are_malformed_not_admission(self) -> None:
        unknown = adapter.deliver(event(), mode="prod", env={})
        self.assertFalse(unknown["ok"])
        self.assertEqual(unknown["state"], adapter.INVALID_MODE_STATE)
        self.assertTrue(unknown["fail_closed"])
        self.assertFalse(unknown["admission_gate"])
        self.assertFalse(unknown["silent_skip"])

        empty = adapter.deliver({}, mode="test", env={})
        self.assertFalse(empty["ok"])
        self.assertEqual(empty["state"], adapter.INVALID_EVENT_STATE)
        self.assertTrue(empty["fail_closed"])
        self.assertFalse(empty["admission_gate"])
        self.assertFalse(empty["silent_skip"])

        missing_text = adapter.deliver({"id": "no-body"}, mode="test", env={})
        self.assertFalse(missing_text["ok"])
        self.assertEqual(missing_text["state"], adapter.INVALID_EVENT_STATE)

    def test_wires_existing_modules_and_does_not_remint_them(self) -> None:
        for path in WIRED:
            self.assertTrue(path.is_file(), path)
        self.assertEqual(adapter.SECRET_ENV, ("SLACK_BOT_TOKEN", "SLACK_APP_TOKEN"))
        self.assertEqual(adapter.GEMINI_SECRET_ENV, adapter.SECRET_ENV)
        self.assertEqual(adapter.DEFAULT_CHANNEL, "C0BRGMDQB6G")
        grok = (ROOT / "integrations" / "grok_slack" / "bridge.py").read_text(encoding="utf-8")
        gemini = (ROOT / "integrations" / "gemini_slack" / "bridge.py").read_text(encoding="utf-8")
        ntfy = (ROOT / "ntfy_relays.py").read_text(encoding="utf-8")
        self.assertIn("def credential_presence", grok)
        self.assertIn("SLACK_BOT_TOKEN", gemini)
        self.assertIn("SLACK_APP_TOKEN", gemini)
        self.assertIn("def relay_message", ntfy)
        source = (ROOT / "host" / "slack_relay_adapter.py").read_text(encoding="utf-8")
        self.assertNotIn("import urllib", source)
        self.assertNotIn("urlopen", source)
        self.assertIn("from integrations.grok_slack.bridge import", source)
        self.assertIn("from integrations.gemini_slack import bridge", source)
        self.assertIn("ntfy_relays.relay_message", source)
        self.assertEqual(adapter.GEMINI_BRIDGE_NAME, "integrations.gemini_slack.bridge")
        self.assertNotIn("RUNTIME_UNCONFIGURED", source)
        self.assertNotIn("LIVE_TRANSPORT_UNINJECTED", source)
        self.assertNotIn("INJECTED_DELIVERED", source)

    def test_self_test_covers_synthetic_test_and_live_uncredentialed(self) -> None:
        with mock.patch("urllib.request.urlopen") as urlopen:
            report = adapter.self_test()
        urlopen.assert_not_called()
        self.assertTrue(report["ok"])
        self.assertEqual(report["synthetic"]["state"], adapter.SYNTHETIC_STATE)
        self.assertEqual(report["live_uncredentialed"]["state"], adapter.SYNTHETIC_STATE)
        self.assertTrue(report["live_uncredentialed"]["ok"])
        self.assertFalse(report["live_uncredentialed"]["fail_closed"])
        self.assertFalse(report["live_uncredentialed"]["admission_gate"])

    def test_cli_self_test_exits_zero(self) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            code = adapter.main(["--self-test"])
        self.assertEqual(code, 0)
        report = json.loads(buf.getvalue())
        self.assertTrue(report["ok"])

    def test_cli_live_with_empty_env_exits_zero(self) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            code = adapter.main(["--mode", "live"])
        self.assertEqual(code, 0)
        receipt = json.loads(buf.getvalue())
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["state"], adapter.SYNTHETIC_STATE)
        self.assertFalse(receipt["admission_gate"])


if __name__ == "__main__":
    unittest.main()
