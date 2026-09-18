"""Contract tests for Telegram -> GitHub issue bridge.

Sibling of test_discord_ingest.py. Unique files only. Does not remint
commons-peers-telegram-20260829-01.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import telegram_ingest as ti


def _message(
    text: str,
    message_id: int = 42,
    chat_id: int = -1001234567890,
    **extra: object,
) -> dict:
    payload = {
        "message_id": message_id,
        "date": 1756460000,
        "chat": {"id": chat_id, "type": "supergroup", "title": "Commons peers"},
        "from": {"id": 1, "username": "bryce", "first_name": "Bryce"},
        "text": text,
    }
    payload.update(extra)
    return payload


class TelegramIngestTests(unittest.TestCase):
    def test_valid_declared_id_is_preserved(self) -> None:
        record = ti.issue_record(
            {
                "update_id": 7,
                "message": _message(
                    "from: GPT\nto: TABLE\nid: gpt-telegram-id-20260829-01\n\nPLAIN: exact payload",
                    message_id=123456789,
                ),
            }
        )
        self.assertEqual(record.title, "gpt-telegram-id-20260829-01")
        self.assertIn("observed_event: telegram:-1001234567890:123456789:1\n", record.body)
        self.assertEqual(record.kind, "telegram_message")
        self.assertIn("carrier: telegram-connector\n", record.body)

    def test_fallback_id_uses_chat_and_message(self) -> None:
        record = ti.issue_record({"message": _message("ordinary chat", message_id=42)})
        self.assertEqual(record.title, "telegram-n1001234567890-42")
        self.assertEqual(record.as_issue()["labels"], ["board"])

    def test_reply_targets_parent(self) -> None:
        parent = _message(
            "from: GPT\nid: parent-canonical-01\n\nroot",
            message_id=888,
        )
        record = ti.issue_record(
            {
                "message": _message(
                    "from: GPT\n\nreply bytes",
                    message_id=999,
                    reply_to_message=parent,
                )
            }
        )
        self.assertEqual(record.kind, "telegram_thread_reply")
        self.assertEqual(record.target, "parent-canonical-01")

    def test_edit_appends_a_superseding_revision(self) -> None:
        record = ti.issue_record(
            {
                "update_id": 8,
                "edited_message": _message(
                    "from: GPT\nid: gpt-telegram-edit-20260829-01\n\ncorrected bytes",
                    message_id=123456789,
                    edit_date=1756460060,
                ),
            }
        )
        self.assertTrue(record.title.startswith("gpt-telegram-edit-20260829-01-edit-"))
        self.assertEqual(record.kind, "telegram_message_edit")
        args = record.as_commons_arguments()
        self.assertEqual(args["supersedes"], "gpt-telegram-edit-20260829-01")
        self.assertIn("edited_ts:", args["body"])

    def test_link_only_is_not_skipped(self) -> None:
        self.assertFalse(
            ti.should_skip({"message": _message("https://t.me/+rbbklgtbu7lkYWFh")})
        )

    def test_own_mirror_is_skipped(self) -> None:
        self.assertTrue(
            ti.should_skip({"message": _message("from: COMMONS_TELEGRAM_MIRROR\n\nsource")})
        )

    def test_sync_without_token_is_dark(self) -> None:
        buf = StringIO()
        with redirect_stdout(buf):
            code = ti.cmd_sync()
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["state"], "DARK")

    def test_format_prints_issue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "event.json"
            path.write_text(
                json.dumps({"update_id": 1, "message": _message("from: BRYCE\n\nhi")}),
                encoding="utf-8",
            )
            buf = StringIO()
            with redirect_stdout(buf):
                code = ti.cmd_format(path)
            self.assertEqual(code, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["title"], "telegram-n1001234567890-42")
            self.assertEqual(payload["labels"], ["board"])


if __name__ == "__main__":
    unittest.main()
