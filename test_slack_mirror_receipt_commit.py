"""Regression for provider-accepted Slack receipts whose state commit fails."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from host import slack_mirror
from host import slack_mirror_state as state

CHANNEL = "C0123456789"


class ReceiptCommitFailureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "receipts.sqlite3"
        self.store = state.MirrorStore(self.path)

    def test_provider_accept_then_receipt_persistence_failure_is_immediately_uncertain(self):
        calls: list[str] = []

        def sender(text: str, _thread: str) -> str:
            calls.append(text)
            return "1789564700.000001"

        original_finish = self.store._finish

        def fail_receipt_finish(*args, **kwargs):
            if kwargs.get("receipt") is not None:
                # Model the receipt-phase SQLite COMMIT failure. The durable
                # in-flight intent was committed before transport and must stay.
                raise state.DeliveryError("simulated receipt commit failure")
            return original_finish(*args, **kwargs)

        with mock.patch.object(self.store, "_finish", side_effect=fail_receipt_finish):
            with self.assertRaises(state.DeliveryUncertain) as caught:
                self.store.send("receipt-commit", ["only"], sender, channel=CHANNEL)

        snapshot = self.store.inspect("receipt-commit", ["only"], channel=CHANNEL)
        self.assertEqual(snapshot["state"], "UNCERTAIN_OR_IN_FLIGHT")
        self.assertEqual(snapshot["receipts"], [])
        self.assertEqual(snapshot["in_flight"]["part"], 0)
        self.assertIn(snapshot["in_flight"]["attempt"], str(caught.exception))
        self.assertEqual(calls, ["only"])

        # A restart/retry sees the exact pending attempt and does not resend.
        restarted = state.MirrorStore(self.path)
        with self.assertRaises(state.DeliveryUncertain):
            restarted.send("receipt-commit", ["only"], sender, channel=CHANNEL)
        self.assertEqual(calls, ["only"])

    def test_cli_maps_delivery_uncertain_to_exit_three(self):
        source = Path(self.temp.name) / "post.md"
        source.write_text("payload", encoding="utf-8")
        with (
            mock.patch.object(slack_mirror, "format_mirror", return_value=["payload"]),
            mock.patch.object(
                slack_mirror,
                "send_parts",
                side_effect=state.DeliveryUncertain("receipt persistence failed"),
            ),
            mock.patch.dict(os.environ, {"SLACK_BOT_TOKEN": "test-only-token"}),
        ):
            result = slack_mirror.main([
                "slack_mirror.py",
                "send",
                str(source),
                "--channel",
                CHANNEL,
                "--event-id",
                "receipt-commit-cli",
                "--state",
                str(self.path),
            ])
        self.assertEqual(result, 3)


if __name__ == "__main__":
    unittest.main()
