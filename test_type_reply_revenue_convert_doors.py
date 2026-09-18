"""Hermetic: reply-to-revenue convert doors cite tips + larger fixed."""
from pathlib import Path
HTML = Path(__file__).resolve().parent / "reply-to-revenue.html"

def test_reply_revenue_convert_doors():
    text = HTML.read_text(encoding="utf-8")
    assert "Convert doors" in text
    assert 'href="./tips.html"' in text
    assert 'href="./diagnostic.html"' in text
    assert 'href="./commercial.html"' in text
    assert "production_survival/README.md" in text
