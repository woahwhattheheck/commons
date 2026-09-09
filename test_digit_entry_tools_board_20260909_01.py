from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_entry_tools_board():
    text = (ROOT / "ENTRY.md").read_text(encoding="utf-8")
    assert "## Tools board (invented tools)" in text
    assert "./job.html" in text
    assert "coil-start-tools-board-20260909-01" in text
