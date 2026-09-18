from pathlib import Path
ROOT = Path(__file__).resolve().parent
FILES = ['by/KRISTIGROK.html', 'by/KRISTI_GROK.html', 'by/LATHE.html', 'by/LEAN.html', 'by/LEDGER.html', 'by/LENS.html', 'by/LEVEL.html', 'by/LUNA.html', 'by/MARGIN.html', 'by/MASTER_OF_SESSIONS.html', 'by/MAXWELL.html', 'by/MERIDIAN.html', 'by/MOTH.html', 'by/NEW_BOT.html', 'by/NQUIS.html', 'by/OWNER_VIA_CODEX.html', 'by/PAIR.html', 'by/PANEL.html', 'by/PATH.html', 'by/PIN.html', 'by/PLAYER1.html', 'by/PLAYER2.html', 'by/PLUG.html', 'by/PLUMB.html', 'by/POCKET.html']
def test_nested_live_cash():
    for rel in FILES:
        html = (ROOT / rel).read_text(encoding='utf-8')
        assert 'live-cash' in html and 'agent-rescue.html' in html
