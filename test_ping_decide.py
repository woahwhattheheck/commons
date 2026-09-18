#!/usr/bin/env python3
"""Routing and quiet-terminal contract for ping/decide.py."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


DECIDE_PATH = Path(__file__).resolve().parent / "ping" / "decide.py"
SPEC = importlib.util.spec_from_file_location("commons_ping_decide", DECIDE_PATH)
D = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(D)


class PingDecideTests(unittest.TestCase):
    def test_adapter_kind(self) -> None:
        self.assertEqual(D.adapter_kind("Cursor Grok Bot desktop agent"), "cursor")
        self.assertEqual(D.adapter_kind("Grok Bot / latch"), "cursor")
        self.assertEqual(D.adapter_kind("ChatGPT Work main chat"), "chatgpt")
        self.assertEqual(
            D.adapter_kind("Claude Code cloud container (Anthropic)"), "claude"
        )
        self.assertEqual(D.adapter_kind("ntfy poll"), "ntfy")

    def test_cursor_doorbell_is_held_while_poll_adapters_advance(self) -> None:
        wake = {
            "actionable": [
                {"from": "GRAVE", "adapter": "ChatGPT Work main chat"},
                {"from": "WIRE", "adapter": "Grok Bot / wire"},
            ]
        }
        mail = {
            "seq": 9,
            "ts": "t",
            "mail": [
                {
                    "to": "GRAVE",
                    "from": "BRYCE",
                    "seq": 3,
                    "id": "a",
                    "ts": "t",
                },
                {
                    "to": "WIRE",
                    "from": "BRYCE",
                    "seq": 4,
                    "id": "b",
                    "ts": "t",
                },
            ],
        }

        out, ping, moved, moved_poll = D.decide(mail, wake, {"claims": {}})

        self.assertEqual(ping, "0")
        self.assertEqual(moved, [])
        self.assertEqual(moved_poll, ["GRAVE"])
        self.assertEqual(out["moved"], moved)
        self.assertEqual(out["moved_poll"], moved_poll)
        self.assertEqual(out["held_cursor"], ["WIRE"])

    def test_own_post_is_quiet(self) -> None:
        wake = {"actionable": [{"from": "WIRE", "adapter": "cursor"}]}
        mail = {
            "mail": [
                {
                    "to": "WIRE",
                    "from": "WIRE",
                    "seq": 8,
                    "id": "self",
                    "ts": "t",
                }
            ]
        }

        out, ping, moved, moved_poll = D.decide(mail, wake, {"claims": {}})

        self.assertEqual(ping, "0")
        self.assertEqual(moved, [])
        self.assertEqual(moved_poll, [])
        self.assertEqual(out["claims"]["WIRE"]["seq"], 8)

    def test_same_checkpoint_has_a_later_quiet_tick(self) -> None:
        wake = {"actionable": [{"from": "WIRE", "adapter": "cursor"}]}
        mail = {
            "seq": 10,
            "ts": "t",
            "mail": [
                {
                    "to": "WIRE",
                    "from": "BRYCE",
                    "seq": 9,
                    "id": "work",
                    "ts": "t",
                }
            ],
        }

        first, ping, moved, moved_poll = D.decide(mail, wake, {"claims": {}})
        self.assertEqual((ping, moved, moved_poll), ("0", [], []))
        self.assertEqual(first["held_cursor"], ["WIRE"])

        later, ping, moved, moved_poll = D.decide(mail, wake, first)
        self.assertEqual((ping, moved, moved_poll), ("0", [], []))
        self.assertEqual(later["claims"], first["claims"])


if __name__ == "__main__":
    unittest.main()
