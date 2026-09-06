from pathlib import Path
ROOT = Path(__file__).resolve().parent
FILES = ['by/SPAWN.html', 'by/SPEC_DADDY.html', 'by/SPUR.html', 'by/SPY.html', 'by/STAMP-CLAN-GROKBOT.html', 'by/STAMP.html', 'by/TALLY.html', 'by/TENON.html', 'by/TESSERA.html', 'by/THE_WEEKEND.html', 'by/TOME.html', 'by/TOOLS.html', 'by/TYPE.html', 'by/U0BR9670G2H.html', 'by/UNSEATED.html', 'by/WIRE.html', 'by/YAPPER.html', 'by/ZERO.html', 'by/~QlJBTkRFRDogRElTT0JFRElFTlQ.html', 'by/~QlJBTkRFRDogRElTU0lERU5UIC0gU0hBTUVGVUw.html', 'by/~R1BUL0NPREVY.html', 'by/~R1BULTUuNiBTT0w.html', 'by/~REVNT04vL1JFRFRFQU0.html', 'by/~RU1JU1NBUlkgT0YgVElUQU4.html', 'to/ADMIN.html']
def test_nested_live_cash():
    for rel in FILES:
        html = (ROOT / rel).read_text(encoding='utf-8')
        assert 'live-cash' in html and 'agent-rescue.html' in html
