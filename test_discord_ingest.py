"""Contract tests for Discord -> GitHub issue bridge."""

from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import discord_ingest as di


class DiscordIngestTests(unittest.TestCase):
    def test_valid_declared_id_is_preserved(self) -> None:
        record = di.issue_record(
            {
                "id": "123456789012345678",
                "channel_id": "111",
                "guild_id": "222",
                "timestamp": "2026-08-24T04:20:00.000000+00:00",
                "content": "from: GPT\nto: TABLE\nid: gpt-discord-id-20260824-01\n\nPLAIN: exact payload",
                "author": {"username": "gpt"},
            }
        )
        self.assertEqual(record.title, "gpt-discord-id-20260824-01")
        self.assertIn("observed_event: discord:222:111:123456789012345678:1\n", record.body)
        self.assertEqual(record.kind, "discord_message")

    def test_fallback_id_is_snowflake(self) -> None:
        record = di.issue_record(
            {
                "id": "123456789012345678",
                "channel_id": "111",
                "content": "ordinary chat",
                "author": {"username": "bryce"},
            }
        )
        self.assertEqual(record.title, "discord-123456789012345678")
        self.assertEqual(record.as_issue()["labels"], ["board"])

    def test_reply_targets_parent(self) -> None:
        record = di.issue_record(
            {
                "id": "999",
                "channel_id": "111",
                "content": "from: GPT\n\nreply bytes",
                "author": {"username": "gpt"},
                "referenced_message": {
                    "id": "888",
                    "content": "from: GPT\nid: parent-canonical-01\n\nroot",
                },
            }
        )
        self.assertEqual(record.kind, "discord_thread_reply")
        self.assertEqual(record.target, "parent-canonical-01")

    def test_link_only_is_not_skipped(self) -> None:
        self.assertFalse(
            di.should_skip({"id": "1", "content": "https://github.com/woahwhattheheck/commons/blob/main/p/x.md"})
        )

    def test_own_mirror_is_skipped(self) -> None:
        self.assertTrue(
            di.should_skip({"id": "1", "content": "from: COMMONS_DISCORD_MIRROR\n\nsource"})
        )

    def test_format_prints_issue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "event.json"
            path.write_text(
                json.dumps(
                    {
                        "id": "42",
                        "channel_id": "c",
                        "content": "from: BRYCE\n\nhi",
                        "author": {"username": "bryce"},
                    }
                ),
                encoding="utf-8",
            )
            buf = StringIO()
            with redirect_stdout(buf):
                code = di.cmd_format(path)
            self.assertEqual(code, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["title"], "discord-42")
            self.assertEqual(payload["labels"], ["board"])


if __name__ == "__main__":
    unittest.main()
