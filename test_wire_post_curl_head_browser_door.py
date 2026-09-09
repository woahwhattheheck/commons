"""ground/POST_CURL.md must land Pages-lag readers on head.html browser door."""
from pathlib import Path

TEXT = (Path(__file__).resolve().parent / "ground/POST_CURL.md").read_text(encoding="utf-8")


def test_post_curl_points_at_head_html_browser_door():
    assert "Contents API" in TEXT
    assert "head.html" in TEXT
    assert "head.html?path=" in TEXT
    assert "Pages" in TEXT and "404" in TEXT
