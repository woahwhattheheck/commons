"""Hermetic: commercial.html mid-ladders to tip-shelf $199."""
from pathlib import Path
HTML = Path(__file__).resolve().parent / "commercial.html"

def test_commercial_tipshelf_midladder():
    text = HTML.read_text(encoding="utf-8")
    assert "Mid-ladder" in text
    for slug in (
        "dealer-service-lead-rescue.html",
        "referral-intake-completeness.html",
        "repair-booking-preflight.html",
        "plant-downtime-handoff.html",
        "tips.html",
    ):
        assert slug in text
