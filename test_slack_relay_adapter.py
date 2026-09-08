#!/usr/bin/env python3
"""Focused contract tests for the read-only Slack destination adapter."""
from __future__ import annotations

import io
import json
import tempfile
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
FIXED_NOW = "2026-09-01T00:00:00Z"


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


class ExplodingInput:
    def __getattribute__(self, name):
        raise AssertionError(f"legacy input was inspected: {name}")


class SlackRelayAdapterTests(unittest.TestCase):
    def test_test_mode_receipt_is_byte_identical_twice(self) -> None:
        first = json.dumps(adapter.deliver(event(), mode="test", now=FIXED_NOW), sort_keys=True)
        second = json.dumps(adapter.deliver(event(), mode="test", now=FIXED_NOW), sort_keys=True)
        self.assertEqual(first, second)

    def test_test_mode_is_synthetic_and_read_only(self) -> None:
        receipt = adapter.deliver(event(), mode="test", now=FIXED_NOW)
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["state"], adapter.SYNTHETIC_STATE)
        self.assertEqual(receipt["schema"], adapter.RECEIPT_SCHEMA)
        self.assertEqual(receipt["mode"], "test")
        self.assertTrue(receipt["synthetic"])
        self.assertFalse(receipt["delivery_pending"])
        self.assertFalse(receipt["real_send"])
        self.assertEqual(receipt["network_calls"], 0)
        self.assertEqual(receipt["transport_invocations"], 0)
        self.assertEqual(receipt["environment_reads"], 0)
        self.assertEqual(receipt["text_classifications"], 0)
        self.assertTrue(receipt["slack_ts"].startswith("synthetic."))

    def test_handoff_succeeds_without_local_connection_state(self) -> None:
        callable_input = mock.Mock(side_effect=AssertionError("callable must not run"))
        receipt = adapter.deliver(
            event(), mode="handoff", env=ExplodingInput(), transport=callable_input, now=FIXED_NOW
        )
        callable_input.assert_not_called()
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["state"], adapter.HANDOFF_STATE)
        self.assertTrue(receipt["delivery_pending"])
        self.assertFalse(receipt["synthetic"])
        self.assertFalse(receipt["real_send"])
        self.assertEqual(receipt["network_calls"], 0)
        self.assertEqual(receipt["transport_invocations"], 0)
        self.assertEqual(receipt["slack_ts"], "")
        self.assertEqual(
            receipt["packet"],
            {
                "schema": adapter.PACKET_SCHEMA,
                "id": "caliper-slack-relay-adapter-01",
                "channel": "C0BRGMDQB6G",
                "text": "synthetic Slack destination ping",
                "thread_ts": "",
                "source_host": "local-uncredentialed",
                "carrier_origin": "discord-direct-root",
            },
        )

    def test_environment_values_do_not_change_or_enter_receipt(self) -> None:
        plain = adapter.deliver(event(), mode="handoff", env={}, now=FIXED_NOW)
        supplied = adapter.deliver(
            event(),
            mode="handoff",
            env={"SLACK_BOT_TOKEN": "xoxb-test-secret", "SLACK_APP_TOKEN": "xapp-test-secret"},
            now=FIXED_NOW,
        )
        self.assertEqual(plain, supplied)
        encoded = json.dumps(supplied)
        self.assertNotIn("xoxb-test-secret", encoded)
        self.assertNotIn("xapp-test-secret", encoded)

    def test_supplied_callable_is_never_invoked_in_either_mode(self) -> None:
        supplied = mock.Mock(side_effect=AssertionError("callable must not run"))
        for mode in adapter.MODES:
            with self.subTest(mode=mode):
                receipt = adapter.deliver(event(), mode=mode, transport=supplied, now=FIXED_NOW)
                self.assertTrue(receipt["ok"])
        supplied.assert_not_called()

    def test_live_mode_is_not_a_send_path(self) -> None:
        supplied = mock.Mock(side_effect=AssertionError("callable must not run"))
        receipt = adapter.deliver(event(), mode="live", env=ExplodingInput(), transport=supplied)
        supplied.assert_not_called()
        self.assertFalse(receipt["ok"])
        self.assertEqual(receipt["state"], adapter.INVALID_MODE_STATE)
        self.assertTrue(receipt["fail_closed"])
        self.assertEqual(receipt["network_calls"], 0)

    def test_message_text_is_forwarded_without_local_classification(self) -> None:
        text = "draft marker remains exact transport data"
        receipt = adapter.deliver(event(text=text), mode="handoff", now=FIXED_NOW)
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["packet"]["text"], text)
        self.assertEqual(receipt["text_classifications"], 0)

    def test_packet_digest_binds_the_exact_packet(self) -> None:
        first = adapter.deliver(event(text="one"), mode="handoff", now=FIXED_NOW)
        second = adapter.deliver(event(text="two"), mode="handoff", now=FIXED_NOW)
        self.assertNotEqual(first["packet_sha256"], second["packet_sha256"])
        raw = json.dumps(first["packet"], ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        import hashlib
        self.assertEqual(first["packet_sha256"], hashlib.sha256(raw.encode("utf-8")).hexdigest())

    def test_ntfy_shaped_event_preserves_origin_and_refuses_id_rewrite(self) -> None:
        ntfy_event = {
            "id": "caller-stable-id",
            "payload": {"id": "caller-stable-id", "body": "same body"},
            "host": "https://relay.example/",
            "source_host": "https://relay.example/",
            "carrier_origin": "https://first.example/",
        }
        receipt = adapter.deliver(ntfy_event, mode="handoff", now=FIXED_NOW)
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["source_host"], "https://relay.example")
        self.assertEqual(receipt["carrier_origin"], "https://first.example")
        payload = json.loads(receipt["packet"]["text"])
        self.assertEqual(payload["id"], "caller-stable-id")
        self.assertEqual(payload["body"], "same body")

        mismatch = dict(ntfy_event)
        mismatch["id"] = "different-id"
        closed = adapter.deliver(mismatch, mode="handoff", now=FIXED_NOW)
        self.assertFalse(closed["ok"])
        self.assertEqual(closed["state"], adapter.INVALID_EVENT_STATE)
        self.assertTrue(closed["fail_closed"])

    def test_unknown_mode_and_empty_event_return_explicit_errors(self) -> None:
        unknown = adapter.deliver(event(), mode="prod", now=FIXED_NOW)
        self.assertFalse(unknown["ok"])
        self.assertEqual(unknown["state"], adapter.INVALID_MODE_STATE)
        self.assertFalse(unknown["silent_skip"])

        for bad in ({}, {"id": "no-body"}, "not-an-object"):
            with self.subTest(bad=bad):
                receipt = adapter.deliver(bad, mode="handoff", now=FIXED_NOW)
                self.assertFalse(receipt["ok"])
                self.assertEqual(receipt["state"], adapter.INVALID_EVENT_STATE)
                self.assertFalse(receipt["silent_skip"])

    def test_wires_existing_modules_without_local_filter_or_connection_checks(self) -> None:
        for path in WIRED:
            self.assertTrue(path.is_file(), path)
        source = (ROOT / "host" / "slack_relay_adapter.py").read_text(encoding="utf-8")
        self.assertIn("ntfy_relays.relay_message", source)
        self.assertIn("from integrations.grok_slack.bridge import DEFAULT_CHANNEL", source)
        self.assertIn("from integrations.gemini_slack import bridge", source)
        self.assertNotIn("credential_presence", source)
        self.assertNotIn("SECRET_ENV", source)
        self.assertNotIn("commons_publication_policy", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("os.environ", source)
        self.assertEqual(adapter.GEMINI_BRIDGE_NAME, "integrations.gemini_slack.bridge")

    def test_self_test_covers_synthetic_and_handoff_paths(self) -> None:
        report = adapter.self_test()
        self.assertTrue(report["ok"])
        self.assertEqual(report["synthetic"]["state"], adapter.SYNTHETIC_STATE)
        self.assertEqual(report["handoff"]["state"], adapter.HANDOFF_STATE)
        self.assertEqual(report["synthetic"]["packet"], report["handoff"]["packet"])

    def test_cli_self_test_exits_zero(self) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            code = adapter.main(["--self-test"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(buf.getvalue())["ok"])

    def test_cli_handoff_reads_input_and_emits_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "event.json"
            source.write_text(json.dumps(event(thread_ts="123.456")), encoding="utf-8")
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                code = adapter.main(["--mode", "handoff", "--input", str(source)])
        self.assertEqual(code, 0)
        receipt = json.loads(buf.getvalue())
        self.assertEqual(receipt["state"], adapter.HANDOFF_STATE)
        self.assertEqual(receipt["packet"]["thread_ts"], "123.456")
        self.assertEqual(receipt["network_calls"], 0)


if __name__ == "__main__":
    unittest.main()
