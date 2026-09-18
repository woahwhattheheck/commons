from pathlib import Path
TEXT=(Path(__file__).resolve().parent/"memory/GROK_LAND_UPFRONT.md").read_text(encoding="utf-8")
def test_live_cash():
    assert "## Live cash" in TEXT
    assert "agent-rescue.html" in TEXT
