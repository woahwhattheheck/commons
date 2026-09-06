from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_goo_read_colloquial():
    md = (ROOT / "ground/CLAUDE_PEER_CHECK.md").read_text(encoding="utf-8")
    assert "GOO READ" in md
    assert "go read" in md
    assert "03_load_path_that_missed" in md
