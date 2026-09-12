from pathlib import Path
TEXT = (Path(__file__).resolve().parent / "AGENTS.md").read_text(encoding="utf-8")

def test_agents_write_roads_include_human_doors():
    assert "writing.html" in TEXT
    assert "reply.html" in TEXT
    assert "WRITE-NOW" in TEXT
    assert "post.html" in TEXT
