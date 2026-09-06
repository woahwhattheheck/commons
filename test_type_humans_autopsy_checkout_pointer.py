"""Hermetic: humans.html distinguishes pack no-checkout from live Autopsy door."""
from pathlib import Path
HTML = Path(__file__).resolve().parent / "humans.html"

def test_humans_autopsy_pointer():
    text = HTML.read_text(encoding="utf-8")
    assert "no checkout of its own" in text
    assert "There is no checkout." not in text
    assert 'href="./agent-rescue.html"' in text
    assert "tools-cash.html" in text
