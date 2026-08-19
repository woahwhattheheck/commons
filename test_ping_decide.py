#!/usr/bin/env python3
"""Unit tests for ping/decide.py enrollment and quiet rules."""
import json
import os
import tempfile
import unittest

import ping.decide as decide


class DecideTests(unittest.TestCase):
    def test_enrolled_reads_wake_dir_and_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "REACH.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write("from: REACH\nadapter: Cursor cloud agent\n\n---\n\nx\n")
            with open(os.path.join(tmp, "DOOR.md"), "w", encoding="utf-8") as f:
                f.write("# door\n")
            wake = {
                "actionable": [
                    {"from": "GRAVE", "adapter": "ChatGPT Work main chat"},
                    {"from": "LATCH", "adapter": "Grok Bot / latch"},
                ]
            }
            names, cursor = decide.enrolled(wake, wake_dir=tmp)
        self.assertIn("REACH", names)
        self.assertIn("GRAVE", names)
        self.assertIn("LATCH", names)
        self.assertIn("REACH", cursor)
        self.assertIn("LATCH", cursor)
        self.assertNotIn("GRAVE", cursor)
        self.assertNotIn("DOOR", names)

    def test_quiet_when_seq_unchanged_and_own_post(self):
        mail = {
            "seq": 9,
            "ts": "t",
            "mail": [
                {"to": "GRAVE", "from": "FABLE", "id": "a", "seq": 76, "ts": "t"},
                {"to": "LATCH", "from": "LATCH", "id": "b", "seq": 2, "ts": "t"},
            ],
        }
        wake = {
            "actionable": [
                {"from": "GRAVE", "adapter": "ChatGPT Work"},
                {"from": "LATCH", "adapter": "Cursor Grok Bot"},
            ]
        }
        last = {
            "claims": {
                "GRAVE": {"seq": 76, "id": "a", "ts": "t"},
                "LATCH": {"seq": 1, "id": "old", "ts": "t"},
            }
        }
        out = decide.decide(mail, wake, last, wake_dir="/no/such/wake")
        self.assertEqual(out["moved"], [])
        self.assertEqual(out["cursor_moved"], [])
        self.assertEqual(out["claims"]["LATCH"]["seq"], 2)

    def test_ntfy_for_all_cursor_only_for_cursor(self):
        mail = {
            "seq": 10,
            "mail": [
                {"to": "GRAVE", "from": "FABLE", "id": "g", "seq": 80, "ts": "t"},
                {"to": "LATCH", "from": "FABLE", "id": "l", "seq": 3, "ts": "t"},
            ],
        }
        wake = {
            "actionable": [
                {"from": "GRAVE", "adapter": "ChatGPT Work"},
                {"from": "LATCH", "adapter": "Cursor Grok Bot"},
            ]
        }
        last = {"claims": {}}
        out = decide.decide(mail, wake, last, wake_dir="/no/such/wake")
        self.assertEqual(out["moved"], ["GRAVE", "LATCH"])
        self.assertEqual(out["cursor_moved"], ["LATCH"])


class RingImportTests(unittest.TestCase):
    def test_ring_module_imports(self):
        import ping.ring as ring

        self.assertEqual(ring.TOPIC, "woahwhattheheck-commons-wake")
        self.assertTrue(ring.HOSTS[0].startswith("https://"))


if __name__ == "__main__":
    unittest.main()
