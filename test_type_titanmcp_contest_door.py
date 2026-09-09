"""Hermetic: titanmcp contest door + webmcp Shared Pad pointer."""
from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_titanmcp_door():
    text = (ROOT / "titanmcp.html").read_text(encoding="utf-8")
    assert "titanmcp" in text
    assert "https://webmcp-pad.vercel.app/" in text
    assert "088c6f781f9d16251220f6004b9929d31e7d109aeffeb71b13e07498ad82686c" in text
    assert "Bryce exact go" in text
    assert "commons-spark-mcp.vercel.app/mcp" in text

def test_webmcp_points_contest_elsewhere():
    text = (ROOT / "webmcp.html").read_text(encoding="utf-8")
    assert 'href="./titanmcp.html"' in text
    assert "Shared Pad" in text
