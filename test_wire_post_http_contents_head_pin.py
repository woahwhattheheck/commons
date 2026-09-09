"""post-http.html must land Contents verify on head.html pin."""
from pathlib import Path

HTML = (Path(__file__).resolve().parent / "post-http.html").read_text(encoding="utf-8")


def test_post_http_contents_api_head_pin():
    assert "p/{id}.md" in HTML
    assert "ntfy 200 is mail" in HTML
    assert 'href="./head.html"' in HTML
    assert "Contents API" in HTML
    assert "head.html?path=" in HTML
