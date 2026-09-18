from pathlib import Path
ROOT = Path(__file__).resolve().parent
FILES = ['embed/demo.html', 'packs/tjlabs-terms.html', 'to/PRODUCTS.html', 'to/OFFER.html', 'to/SWARM_OFFER.html', 'to/MARGIN.html', 'to/SALVAGE.html', 'to/TOOLS.html']

def test_nested_live_cash():
    for rel in FILES:
        html = (ROOT / rel).read_text(encoding="utf-8")
        assert "live-cash" in html and "agent-rescue.html" in html
