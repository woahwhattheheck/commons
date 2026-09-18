"""nojs.html must land Contents/Git Data readers on head.html pin."""
from pathlib import Path

HTML = (Path(__file__).resolve().parent / "nojs.html").read_text(encoding="utf-8")


def test_nojs_contents_api_head_pin():
    assert "Contents/Git Data" in HTML or "Contents API" in HTML
    assert 'href="./head.html"' in HTML
    assert "head.html?path=" in HTML
    assert "p/{id}.md" in HTML
    assert "ntfy 200 is mail" in HTML
