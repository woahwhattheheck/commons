"""Hermetic: grounding.html Live cash names Autopsy $29 + tip-shelf."""
from pathlib import Path
HTML = Path(__file__).resolve().parent / "grounding.html"

def test_grounding_live_cash():
    text = HTML.read_text(encoding="utf-8")
    assert 'id="live-cash"' in text
    assert 'href="./agent-rescue.html"' in text
    for slug in (
        "dealer-service-lead-rescue.html",
        "referral-intake-completeness.html",
        "repair-booking-preflight.html",
        "plant-downtime-handoff.html",
        "tools-cash.html",
    ):
        assert slug in text
