"""wire.html (shared super MCP) must door vanished lands to failed.html."""
from pathlib import Path

HTML = (Path(__file__).resolve().parent / "wire.html").read_text(encoding="utf-8")


def test_wire_html_failed_visibility():
    assert "failed.html" in HTML
    assert "WINDOW_MISS" in HTML
    assert "head.html" not in HTML
    assert "contents/p/" not in HTML
