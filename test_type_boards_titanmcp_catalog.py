"""Hermetic: boards.html catalogs titanmcp contest door."""
from pathlib import Path
HTML = Path(__file__).resolve().parent / "boards.html"

def test_boards_titanmcp_catalog():
    text = HTML.read_text(encoding="utf-8")
    assert 'href="./titanmcp.html"' in text
    assert 'href="./webmcp.html"' in text
