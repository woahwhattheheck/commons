import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("commons_discord_bridge.py")
SPEC = importlib.util.spec_from_file_location("bridge", PATH)
bridge = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = bridge
SPEC.loader.exec_module(bridge)


class BridgeTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
