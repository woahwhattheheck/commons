#!/usr/bin/env python3
"""Local check for poll vs Cursor quota hold. No network. No dest."""
from decide import adapter_kind, decide, enroll


def test_kinds():
    assert adapter_kind("ChatGPT Work main chat") == "chatgpt"
    assert adapter_kind("Claude Code cloud container") == "claude"
    assert adapter_kind("Grok Bot / wire") == "cursor"
    assert adapter_kind("ntfy poll topic") == "ntfy"


def test_poll_does_not_ring_cursor():
    wake = {
        "actionable": [
            {"from": "WIRE", "adapter": "Grok Bot / wire"},
            {"from": "GRAVE", "adapter": "ChatGPT Work main chat"},
            {"from": "MARGIN", "adapter": "Claude Code cloud container"},
        ]
    }
    cursor, poll = enroll(wake, extra_cursor=set())
    assert cursor == {"WIRE"}
    assert poll == {"GRAVE", "MARGIN"}
    mail = {
        "seq": 9,
        "ts": "t",
        "mail": [
            {"to": "GRAVE", "from": "TABLE", "seq": 2, "id": "a", "ts": "t"},
            {"to": "WIRE", "from": "TABLE", "seq": 3, "id": "b", "ts": "t"},
        ],
    }
    out, ping, moved, moved_poll = decide(mail, wake, {"claims": {}})
    assert ping == "0"
    assert moved == []
    assert moved_poll == ["GRAVE"]
    assert "WIRE" not in moved_poll
    assert out["held_cursor"] == ["WIRE"]
    assert out["moved"] == []
    assert out["claims"]["WIRE"]["seq"] == 3


if __name__ == "__main__":
    test_kinds()
    test_poll_does_not_ring_cursor()
    print("ok")
