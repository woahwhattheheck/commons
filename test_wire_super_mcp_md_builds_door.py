from pathlib import Path
TEXT = (Path(__file__).resolve().parent / "ground/WIRE_SUPER_MCP.md").read_text(encoding="utf-8")

def test_wire_super_mcp_md_cites_builds():
    assert "builds.html" in TEXT
    assert "wire.html" in TEXT
