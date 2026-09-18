from pathlib import Path
TEXT = (Path(__file__).resolve().parent / "AGENTS.md").read_text(encoding="utf-8")

def test_agents_cites_builds_and_wire():
    assert "builds.html" in TEXT
    assert "wire.html" in TEXT
