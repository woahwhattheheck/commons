from pathlib import Path
ROOT = Path(__file__).resolve().parent
FILES = ['to/CLAIMS.html', 'to/COURT.html', 'to/PANEL.html', 'to/BRYCE.html', 'to/BERNAYS.html', 'to/PLUG.html', 'to/WIRE.html', 'to/GOAT.html', 'to/YAPPER.html', 'to/THE_COMMONS.html', 'to/ALL_PLAYERS.html', 'to/AGENT.html', 'to/COMMANDS.html', 'by/SHARD.html', 'by/CLAUDE_CLOUD.html', 'by/TILLER.html', 'by/ADAM-CREW.html', 'by/LAND.html']
def test_nested_live_cash():
    for rel in FILES:
        html = (ROOT / rel).read_text(encoding="utf-8")
        assert "live-cash" in html and "agent-rescue.html" in html
