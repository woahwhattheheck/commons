from pathlib import Path
TEXT = (Path(__file__).resolve().parent / "tools.html").read_text(encoding="utf-8")

def test_tools_super_mcp_hook_cites_builds():
    assert 'id="super-mcp-hook"' in TEXT
    assert 'href="./builds.html"' in TEXT
    assert 'href="./wire.html"' in TEXT
