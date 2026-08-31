"""Contract tests for Discord -> GitHub issue bridge."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

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

    def test_edit_appends_a_superseding_revision(self) -> None:
        record = di.issue_record(
            {
                "id": "123456789012345678",
                "channel_id": "111",
                "timestamp": "2026-08-24T04:20:00Z",
                "edited_timestamp": "2026-08-24T04:21:00Z",
                "content": "from: GPT\nid: gpt-discord-edit-20260824-01\n\ncorrected bytes",
                "author": {"username": "gpt"},
            }
        )
        self.assertTrue(record.title.startswith("gpt-discord-edit-20260824-01-edit-"))
        self.assertEqual(record.kind, "discord_message_edit")
        args = record.as_commons_arguments()
        self.assertEqual(args["supersedes"], "gpt-discord-edit-20260824-01")
        self.assertIn("edited_ts: 2026-08-24T04:21:00Z", args["body"])

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

    def test_issue_exists_lists_open_board_issues_once(self) -> None:
        client = di.GitHubClient("token")
        paths: list[str] = []

        def request(method: str, path: str, payload: dict | None = None):
            paths.append(path)
            self.assertNotIn("/search/", path)
            if path.endswith("&page=1"):
                return [{"title": "keep-me"}] + [{"title": "page1-%s" % i} for i in range(99)]
            if path.endswith("&page=2"):
                return [{"title": "last-open"}, {"title": "pr-title", "pull_request": {"url": "https://x"}}]
            raise AssertionError(path)

        client.request = request  # type: ignore[method-assign]
        self.assertTrue(client.issue_exists("keep-me"))
        self.assertTrue(client.issue_exists("last-open"))
        self.assertFalse(client.issue_exists("pr-title"))
        self.assertFalse(client.issue_exists("missing"))
        self.assertEqual(sum(1 for path in paths if "/issues?" in path), 2)
        self.assertTrue(all("/search/" not in path for path in paths))

    def test_sync_creates_missing_titles_without_search(self) -> None:
        events = [
            {"id": "1", "channel_id": "c", "content": "hello one", "author": {"username": "a"}},
            {"id": "2", "channel_id": "c", "content": "hello two", "author": {"username": "a"}},
            {"id": "3", "channel_id": "c", "content": "hello three", "author": {"username": "a"}},
        ]
        paths: list[str] = []
        created: list[str] = []

        class FakeDiscord:
            def __init__(self, _token: str) -> None:
                pass

            def events(self) -> list[dict]:
                return events

        class FakeGitHub(di.GitHubClient):
            def request(self, method: str, path: str, payload: dict | None = None):
                paths.append(path)
                if "/search/" in path:
                    raise di.IngestError("GitHub HTTP 403: search must not be used")
                if method == "GET" and "/issues?" in path:
                    return [{"title": "discord-1"}]
                if method == "POST" and path.endswith("/issues"):
                    created.append(str((payload or {}).get("title")))
                    return {"html_url": "https://github.test/issues/9"}
                raise AssertionError(path)

        buf = StringIO()
        with (
            mock.patch.object(di, "DiscordClient", FakeDiscord),
            mock.patch.object(di, "GitHubClient", FakeGitHub),
            mock.patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "d", "GITHUB_TOKEN": "g"}),
            redirect_stdout(buf),
        ):
            code = di.cmd_sync()
        self.assertEqual(code, 0)
        self.assertTrue(all("/search/" not in path for path in paths))
        self.assertEqual(sum(1 for path in paths if "/issues?" in path), 1)
        self.assertEqual(created, ["discord-2", "discord-3"])
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["planned"], 3)
        self.assertEqual([row["id"] for row in payload["created"]], ["discord-2", "discord-3"])

    def test_github_403_rate_limit_still_fails_closed(self) -> None:
        class FakeDiscord:
            def __init__(self, _token: str) -> None:
                pass

            def events(self) -> list[dict]:
                return [{"id": "1", "channel_id": "c", "content": "hello", "author": {"username": "a"}}]

        class FakeGitHub(di.GitHubClient):
            def request(self, method: str, path: str, payload: dict | None = None):
                raise di.IngestError(
                    'GitHub HTTP 403: {"message": "API rate limit exceeded for installation."}'
                )

        with (
            mock.patch.object(di, "DiscordClient", FakeDiscord),
            mock.patch.object(di, "GitHubClient", FakeGitHub),
            mock.patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "d", "GITHUB_TOKEN": "g"}),
        ):
            with self.assertRaises(di.IngestError) as ctx:
                di.cmd_sync()
        self.assertIn("403", str(ctx.exception))
        self.assertIn("rate limit exceeded for installation", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
