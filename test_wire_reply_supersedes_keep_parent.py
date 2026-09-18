"""reply.html must teach supersedes keeps parent / new id."""
from pathlib import Path

HTML = (Path(__file__).resolve().parent / "reply.html").read_text(encoding="utf-8")


def test_reply_html_supersedes_keep_parent():
    assert "supersedes" in HTML
    assert "new" in HTML.lower() or "<b>new</b>" in HTML
    assert "Do not remint" in HTML or "do not remint" in HTML.lower()
    assert "failed.html" not in HTML
    assert "337" not in HTML
