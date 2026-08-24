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


if __name__ == "__main__":
    unittest.main()
