"""Hermetic: resources.html discovers titanmcp contest + Shared Pad."""
from pathlib import Path
HTML = Path(__file__).resolve().parent / "resources.html"

def test_resources_titanmcp_discovery():
    text = HTML.read_text(encoding="utf-8")
    assert 'href="./titanmcp.html"' in text
    assert 'href="./webmcp.html"' in text
    assert "webmcp-pad.vercel.app" in text
    assert "commons-spark-mcp.vercel.app/mcp" in text
