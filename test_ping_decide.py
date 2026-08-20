#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ping"))
import decide as D


def test_adapter_kind():
    assert D.adapter_kind("Cursor Grok Bot desktop agent") == "cursor"
    assert D.adapter_kind("Grok Bot / latch") == "cursor"
    assert D.adapter_kind("ChatGPT Work main chat") == "chatgpt"
    assert D.adapter_kind("Claude Code cloud container (Anthropic)") == "claude"
    assert D.adapter_kind("ntfy poll") == ""


def test_cursor_doorbell_not_poll():
    wake = {"actionable": [
        {"from": "GRAVE", "adapter": "ChatGPT Work main chat"},
        {"from": "WIRE", "adapter": "Grok Bot / wire"},
    ]}
    mail = {"seq": 9, "ts": "t", "mail": [
        {"to": "GRAVE", "from": "BRYCE", "seq": 3, "id": "a", "ts": "t"},
        {"to": "WIRE", "from": "BRYCE", "seq": 4, "id": "b", "ts": "t"},
    ]}
    out, ping, moved = D.decide(mail, wake, {"claims": {}})
    assert ping == "1"
    assert moved == ["WIRE"]
    assert out["moved_poll"] == ["GRAVE"]


def test_own_post_is_quiet():
    wake = {"actionable": [{"from": "WIRE", "adapter": "cursor"}]}
    mail = {"mail": [{"to": "WIRE", "from": "WIRE", "seq": 8, "id": "self", "ts": "t"}]}
    out, ping, moved = D.decide(mail, wake, {"claims": {}})
    assert ping == "0"
    assert moved == []


if __name__ == "__main__":
    test_adapter_kind()
    test_cursor_doorbell_not_poll()
    test_own_post_is_quiet()
    print("PASS test_ping_decide.py")
