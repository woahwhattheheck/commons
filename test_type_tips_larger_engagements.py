"""Hermetic: tips.html points larger fixed engagements."""
from pathlib import Path
HTML = Path(__file__).resolve().parent / "tips.html"

def test_tips_larger_engagements():
    text = HTML.read_text(encoding="utf-8")
    assert "Larger fixed engagements" in text
    assert 'href="./diagnostic.html"' in text
    assert 'href="./commercial.html"' in text
