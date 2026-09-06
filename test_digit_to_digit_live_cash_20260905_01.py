from pathlib import Path
ROOT = Path(__file__).resolve().parent
FILES = [
    "to/DIGIT.html",
    "door/index.html",
    "ground/index.html",
    "packs/waitlist.html",
    "packs/thanks.html",
]
def test_live_cash_nested():
    for rel in FILES:
        html = (ROOT / rel).read_text(encoding="utf-8")
        assert "live-cash" in html
        assert "agent-rescue.html" in html
