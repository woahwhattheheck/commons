"""head.html must not treat 337 as law; keep Contents API / post-id truth."""
from pathlib import Path

HTML = (Path(__file__).resolve().parent / "head.html").read_text(encoding="utf-8")


def test_head_html_no_337_ritual():
    assert "337 NO" not in HTML
    assert "fire 337" not in HTML
    assert "p/{id}.md" in HTML
    assert "contents API" in HTML
