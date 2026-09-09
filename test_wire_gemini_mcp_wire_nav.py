from pathlib import Path
HTML = (Path(__file__).resolve().parent / "gemini-mcp.html").read_text(encoding="utf-8")

def test_gemini_mcp_nav_includes_wire_html():
    assert 'href="./wire.html"' in HTML
    assert "super-mcp.html" in HTML
