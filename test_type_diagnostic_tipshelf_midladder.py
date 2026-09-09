"""Hermetic: diagnostic.html mid-ladders tip-shelf between Autopsy and $12k."""
from pathlib import Path
HTML = Path(__file__).resolve().parent / "diagnostic.html"

def test_diagnostic_tipshelf_midladder():
    text = HTML.read_text(encoding="utf-8")
    assert "Mid-ladder" in text
    assert "Between Autopsy $29 and this $12k" in text
    for slug in (
        "dealer-service-lead-rescue.html",
        "referral-intake-completeness.html",
        "repair-booking-preflight.html",
        "plant-downtime-handoff.html",
        "tips.html",
    ):
        assert slug in text
