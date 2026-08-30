import importlib.util
import io
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock


PATH = Path(__file__).with_name("commons_discord_bridge.py")
SPEC = importlib.util.spec_from_file_location("bridge", PATH)
bridge = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = bridge
SPEC.loader.exec_module(bridge)


class BridgeTest(unittest.TestCase):
    def test_request_json_honors_retry_after_on_http_429(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b'{"id":"delivered"}'

        limited = urllib.error.HTTPError(
            "https://discord.test/messages", 429, "rate limited",
            {"Retry-After": "9"}, io.BytesIO(b'{"retry_after":0.25}'),
        )
        with mock.patch.object(bridge.urllib.request, "urlopen", side_effect=[limited, Response()]) as opened:
            with mock.patch.object(bridge.time, "sleep") as slept:
                result = bridge.request_json("https://discord.test/messages", method="POST", body={"x": 1})

        self.assertEqual(result, {"id": "delivered"})
        self.assertEqual(opened.call_count, 2)
        slept.assert_called_once_with(0.25)

    def test_request_json_does_not_retry_non_rate_limit_errors(self):
        failed = urllib.error.HTTPError(
            "https://discord.test/messages", 403, "forbidden", {}, io.BytesIO(b"{}"),
        )
        with mock.patch.object(bridge.urllib.request, "urlopen", side_effect=failed) as opened:
            with mock.patch.object(bridge.time, "sleep") as slept:
                with self.assertRaises(urllib.error.HTTPError):
                    bridge.request_json("https://discord.test/messages")

        self.assertEqual(opened.call_count, 1)
        slept.assert_not_called()

    def test_rate_limit_delay_falls_back_to_header_and_caps_wait(self):
        limited = urllib.error.HTTPError(
            "https://discord.test/messages", 429, "rate limited",
            {"Retry-After": "999"}, io.BytesIO(b""),
        )
        self.assertEqual(bridge.rate_limit_delay(limited), 60.0)

    def test_event_id_is_stable(self):
        a = bridge.event_id("github", "delivery-1", {"x": 1})
        b = bridge.event_id("github", "delivery-1", {"x": 2})
        self.assertEqual(a, b)

    def test_journal_deduplicates_and_replays(self):
        with tempfile.TemporaryDirectory() as td:
            j = bridge.Journal(Path(td) / "events.sqlite3")
            event, inserted = j.append("slack", "message", "123.4", {"text": "hello"})
            self.assertTrue(inserted)
            _, inserted_again = j.append("slack", "message", "123.4", {"text": "changed"})
            self.assertFalse(inserted_again)
            self.assertEqual([event.id], [x.id for x in j.pending("discord")])
            j.delivered(event, "discord", "remote")
            self.assertEqual([], j.pending("discord"))
            j.db.close()

    def test_journal_resolves_discord_reply_target(self):
        with tempfile.TemporaryDirectory() as td:
            j = bridge.Journal(Path(td) / "events.sqlite3")
            event, _ = j.append("model", "commons.post", "native", {"canonical_id": "root-01"})
            j.delivered(event, "discord", "998877")
            self.assertEqual(j.delivery_for_canonical("root-01", "discord"), "998877")
            j.db.close()

    def test_render_prevents_broadcast_mentions(self):
        event = bridge.Event("id", "slack", "message", "1", {"text": "@everyone @here"}, 0)
        rendered = bridge.render(event)
        self.assertNotIn("@everyone", rendered)
        self.assertIn("commons:id", rendered)

    def test_discord_to_commons_uses_canonical_issue_road_once(self):
        class FakeGitHub:
            def __init__(self):
                self.created = []

            def issue_exists(self, title):
                return False

            def create_issue(self, record):
                self.created.append(record)
                return "https://github.test/issues/1"

        with tempfile.TemporaryDirectory() as td:
            journal = bridge.Journal(Path(td) / "events.sqlite3")
            raw = {
                "id": "123456789012345678",
                "channel_id": "111",
                "guild_id": "222",
                "timestamp": "2026-08-24T18:00:00Z",
                "content": "from: GEMINI\nid: gemini-discord-20260824-01\n\nhello Commons",
                "author": {"username": "gemini"},
            }
            event, _ = journal.append(
                "discord", "message", raw["id"], {"discord_event": raw}
            )
            fake = FakeGitHub()
            previous = bridge.JOURNAL
            bridge.JOURNAL = journal
            try:
                bridge.deliver_commons_issue(fake)
                bridge.deliver_commons_issue(fake)
            finally:
                bridge.JOURNAL = previous
                journal.db.close()
        self.assertEqual(len(fake.created), 1)
        self.assertEqual(fake.created[0].title, "gemini-discord-20260824-01")

    def test_public_commons_mcp_receives_lossless_append_post(self):
        calls = []
        previous = bridge.request_json
        bridge.request_json = lambda url, **kwargs: calls.append((url, kwargs)) or {
            "result": {"structuredContent": {"git_sha": "abc123"}}
        }
        try:
            record = bridge.discord_ingest.issue_record({
                "id": "123456789012345678", "channel_id": "111",
                "content": "from: GPT\nid: discord-mcp-01\n\nexact body",
                "author": {"username": "gpt"},
            })
            self.assertEqual(bridge.CommonsMCPClient("https://commons.test/mcp").append_record(record), "abc123")
        finally:
            bridge.request_json = previous
        self.assertEqual(calls[0][1]["body"]["params"]["name"], "append_post")
        args = calls[0][1]["body"]["params"]["arguments"]
        self.assertEqual(args["id"], "discord-mcp-01")
        self.assertIn("exact body", args["body"])

    def test_repo_events_route_to_their_named_discord_surfaces(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "p").mkdir()
            (repo / "p" / "slack.md").write_text(
                "from: BRYCE\nid: slack-01\ncarrier: slack-connector\nsubject: Slack root\n\nhello",
                encoding="utf-8",
            )
            self.assertEqual(bridge.repo_event(repo, "head", "A", "p/slack.md")[0], "slack")
            (repo / "p" / "model.md").write_text(
                "from: GPT\nid: model-01\nis_language_model: YES\nmodel: Codex\n\nwork",
                encoding="utf-8",
            )
            source, kind, payload = bridge.repo_event(repo, "head", "A", "p/model.md")
            self.assertEqual((source, kind), ("model", "commons.post"))
            self.assertEqual(payload["canonical_id"], "model-01")
            self.assertEqual(bridge.repo_event(repo, "head", "M", "titan/runner.py")[0], "machine")
            self.assertEqual(bridge.repo_event(repo, "head", "M", "README.md")[0], "repository")


if __name__ == "__main__":
    unittest.main()
