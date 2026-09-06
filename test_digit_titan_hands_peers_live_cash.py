from pathlib import Path
TEXT=(Path(__file__).resolve().parents[1]/"docs"/"TITAN_HANDS_PEERS.md").read_text(encoding="utf-8")
def test_titan_hands_peers_live_cash():
    assert "## Live cash" in TEXT
    assert "agent-rescue.html" in TEXT
    assert "$29" in TEXT
