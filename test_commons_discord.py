"""Contract tests for the lightweight Commons <-> Discord operator CLI."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import commons_discord as cd


class CommonsDiscordTests(unittest.TestCase):
    def test_doctor_reports_both_dark_lanes_without_leaking_secrets(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            report = cd.doctor()
        rendered = json.dumps(report)
        self.assertEqual(report["state"], "DARK")
        self.assertEqual(report["commons_to_discord"]["state"], "DARK")
        self.assertEqual(report["discord_to_commons"]["state"], "DARK")
        self.assertNotIn("secret-token", rendered)

    def test_doctor_accepts_webhook_out_and_bot_plus_github_in(self) -> None:
        configured = {
            "DISCORD_BOT_TOKEN": "secret-token",
            "DISCORD_WEBHOOK_URL": "https://discord.invalid/secret-hook",
            "GITHUB_TOKEN": "secret-github",
            "DISCORD_GUILD_ID": "123",
            "DISCORD_CHANNEL_MODELS": "456",
        }
        with patch.dict(os.environ, configured, clear=True):
            report = cd.doctor()
        rendered = json.dumps(report)
        self.assertEqual(report["state"], "READY")
        self.assertEqual(report["commons_to_discord"]["transport"], "webhook")
        self.assertEqual(report["discord_to_commons"]["state"], "READY")
        self.assertEqual(report["topology"]["configured_channel_names"], ["DISCORD_CHANNEL_MODELS"])
        for secret in configured.values():
            self.assertNotIn(secret, rendered)

    def test_to_discord_format_uses_canonical_mirror(self) -> None:
        record = "---\nfrom: GPT\nid: gpt-discord-cli-20260824-01\n---\nPLAIN: same table.\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gpt-discord-cli-20260824-01.md"
            path.write_text(record, encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                code = cd.main(["to-discord", "format", str(path)])
        self.assertEqual(code, 0)
        self.assertIn("from: COMMONS_DISCORD_MIRROR", output.getvalue())
        self.assertIn("PLAIN: same table.", output.getvalue())

    def test_from_discord_format_preserves_declared_id_and_reply(self) -> None:
        event = {
            "id": "999",
            "channel_id": "111",
            "guild_id": "222",
            "content": "from: GPT\nid: gpt-discord-reply-20260824-01\n\nreply",
            "author": {"username": "gpt"},
            "referenced_message": {
                "id": "888",
                "content": "from: BRYCE\nid: bryce-discord-root-20260824-01\n\nroot",
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "event.json"
            path.write_text(json.dumps(event), encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                code = cd.main(["from-discord", "format", str(path)])
        payload = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(payload["title"], "gpt-discord-reply-20260824-01")
        self.assertIn("target: bryce-discord-root-20260824-01", payload["body"])


if __name__ == "__main__":
    unittest.main()
