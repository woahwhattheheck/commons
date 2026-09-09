"""Hermetic: start.html Live cash matches Autopsy $29 + tip-shelf diagnostics."""
from pathlib import Path
HTML = Path(__file__).resolve().parent / "start.html"

def test_start_html_live_cash():
    text = HTML.read_text(encoding="utf-8")
    assert 'id="live-cash"' in text
    assert 'href="./agent-rescue.html"' in text
    for slug in (
        "dealer-service-lead-rescue.html",
        "referral-intake-completeness.html",
        "repair-booking-preflight.html",
        "plant-downtime-handoff.html",
    ):
        assert slug in text
