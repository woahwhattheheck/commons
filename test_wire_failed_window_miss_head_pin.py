"""failed.html must land WINDOW_MISS / durable gaps on Contents API pin."""
from pathlib import Path

HTML = (Path(__file__).resolve().parent / "failed.html").read_text(encoding="utf-8")


def test_failed_html_window_miss_points_at_head_contents_api():
    assert "WINDOW_MISS" in HTML
    assert 'href="./head.html"' in HTML
    assert "Contents API" in HTML
    assert "head.html?path=" in HTML
    assert "encodeURIComponent(id)" in HTML
