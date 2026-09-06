from pathlib import Path
HTML=(Path(__file__).resolve().parents[1]/"action.html").read_text(encoding="utf-8")
def test_action_pad_live_cash():
    assert 'id="live-cash"' in HTML
    assert "agent-rescue.html" in HTML
    assert "$29" in HTML
    assert "dealer-service-lead-rescue.html" in HTML
