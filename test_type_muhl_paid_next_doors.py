"""Hermetic: muhlnickel-free-sample Paid next doors include tips + diagnostic."""
from pathlib import Path
HTML = Path(__file__).resolve().parent / "muhlnickel-free-sample.html"

def test_muhl_paid_next_doors():
    text = HTML.read_text(encoding="utf-8")
    assert "Paid next doors" in text
    assert 'href="./tips.html"' in text
    assert 'href="./diagnostic.html"' in text
