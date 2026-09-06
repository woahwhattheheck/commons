"""Hermetic: index.html discovers titanmcp contest + Commons Shared Pad."""
from pathlib import Path
HTML = Path(__file__).resolve().parent / "index.html"

def test_index_titanmcp_door_btns():
    text = HTML.read_text(encoding="utf-8")
    assert 'href="./titanmcp.html"' in text
    assert 'href="./webmcp.html"' in text
