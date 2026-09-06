from pathlib import Path
ROOT = Path(__file__).resolve().parent
FILES = ['to/SPUR.html', 'to/SPY.html', 'to/STAMP.html', 'to/SWARM.html', 'to/TABLEREVENUE_FULFILLMENT.html', 'to/TABLEREVENUE_QUALIFICATION.html', 'to/TABLETITAN.html', 'to/THE_WEEKEND.html', 'to/TYPE.html', 'to/UNSEATED.html', 'to/UNSEATEDCLAUDES.html', 'to/WAKE.html', 'to/WEATHER.html', 'to/WORLD.html', 'to/ZERO.html', 'to/index.html', 'to/~Q09NTU9OUyAvIE5PTkRVUExJQ0FUSU5HIElOVEVHUkFUT1I.html', 'to/~R1BULCBHRU1JTkksIFRBQkxF.html']
def test_nested_live_cash():
    for rel in FILES:
        html = (ROOT / rel).read_text(encoding='utf-8')
        assert 'live-cash' in html and 'agent-rescue.html' in html
