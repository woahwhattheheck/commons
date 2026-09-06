from pathlib import Path
HTML=(Path(__file__).resolve().parents[1]/"commons-flowchart.html").read_text(encoding="utf-8")
def test_live_cash():
    assert "live-cash" in HTML and "agent-rescue.html" in HTML
