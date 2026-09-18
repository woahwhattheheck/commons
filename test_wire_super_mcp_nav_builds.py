from pathlib import Path
TEXT = (Path(__file__).resolve().parent / "super-mcp.html").read_text(encoding="utf-8")

def test_super_mcp_nav_cites_builds():
    assert 'href="./builds.html"' in TEXT
    assert 'href="./wire.html"' in TEXT
