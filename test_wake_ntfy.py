#!/usr/bin/env python3
# ntfy is reach. These checks lock the FROM-FILE contract so a later
# rewrite cannot silently invent a second host list or fire the board topic.
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "ping"))

import ntfy_relays
import ping.decide as decide
import ping.ntfy as wake_ntfy


class WakeNtfyFromFile(unittest.TestCase):
    def test_hosts_are_ntfy_relays(self):
        self.assertEqual(wake_ntfy.HOSTS, ntfy_relays.HOSTS)
        self.assertGreaterEqual(len(wake_ntfy.HOSTS), 2)

    def test_wake_topic_is_not_the_board(self):
        self.assertEqual(wake_ntfy.WAKE_TOPIC, "woahwhattheheck-commons-wake")
        self.assertNotEqual(wake_ntfy.WAKE_TOPIC, wake_ntfy.BOARD_TOPIC)
        self.assertNotEqual(wake_ntfy.WAKE_TOPIC, ntfy_relays.TOPIC)

    def test_pack_is_thin_and_under_cap(self):
        names, body = wake_ntfy.pack(["reach", " LATCH "], mail_seq=153)
        self.assertEqual(names, ["REACH", "LATCH"])
        self.assertLessEqual(len(body), wake_ntfy.MAX_BYTES)
        self.assertIn('"kind":"WAKE"', body)
        self.assertNotIn("woahwhattheheck-commons-board", body)

    def test_post_walks_hosts_and_stops_on_200(self):
        class Resp:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        with mock.patch("ping.ntfy.urllib.request.urlopen", return_value=Resp()) as opener:
            host, status = wake_ntfy.post_wake(["REACH"])
        self.assertEqual(status, 200)
        self.assertEqual(host, ntfy_relays.HOSTS[0].rstrip("/"))
        self.assertEqual(opener.call_count, 1)
        req = opener.call_args[0][0]
        self.assertIn(wake_ntfy.WAKE_TOPIC, req.full_url)
        self.assertNotIn(wake_ntfy.BOARD_TOPIC, req.full_url)


class DecideUniversal(unittest.TestCase):
    def test_ntfy_fires_for_any_enrolled_mail_move(self):
        wake = {
            "actionable": [
                {"from": "GRAVE", "adapter": "ChatGPT Work"},
                {"from": "LATCH", "adapter": "Grok Bot / latch; Cursor"},
            ]
        }
        mail = {
            "seq": 9,
            "ts": "2026-08-19T22:00:00Z",
            "mail": [
                {"to": "GRAVE", "from": "TABLE", "seq": 2, "id": "a", "ts": "t"},
                {"to": "LATCH", "from": "TABLE", "seq": 3, "id": "b", "ts": "t"},
            ],
        }
        out = decide.decide(mail, wake, {"claims": {}})
        self.assertEqual(out["moved"], ["GRAVE", "LATCH"])
        self.assertEqual(out["cursor_moved"], ["LATCH"])

    def test_own_post_and_same_seq_stay_quiet(self):
        wake = {"actionable": [{"from": "REACH", "adapter": "ntfy poll"}]}
        mail = {
            "mail": [
                {"to": "REACH", "from": "REACH", "seq": 4, "id": "own", "ts": "t"},
            ]
        }
        out = decide.decide(mail, wake, {"claims": {}})
        self.assertEqual(out["moved"], [])
        again = decide.decide(
            mail,
            wake,
            {"claims": {"REACH": {"seq": 4, "id": "own", "ts": "t"}}},
        )
        self.assertEqual(again["moved"], [])

    def test_github_output_has_ntfy_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out")
            decide.write_github_output(path, "0", [], "1", ["GRAVE"], mail_seq=9)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        self.assertIn("ping=0\n", text)
        self.assertIn("ntfy=1\n", text)
        self.assertIn("ntfy_claims=GRAVE\n", text)
        self.assertIn("mail_seq=9\n", text)


if __name__ == "__main__":
    unittest.main()
