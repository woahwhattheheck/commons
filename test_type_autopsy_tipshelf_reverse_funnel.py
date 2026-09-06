"""Hermetic: agent-rescue.html reverse-funnels to tip-shelf $199 pages."""
from pathlib import Path
HTML = Path(__file__).resolve().parent / "agent-rescue.html"

def test_autopsy_tipshelf_reverse_funnel():
    text = HTML.read_text(encoding="utf-8")
    for slug in (
        "dealer-service-lead-rescue.html",
        "referral-intake-completeness.html",
        "repair-booking-preflight.html",
        "plant-downtime-handoff.html",
        "tips.html",
    ):
        assert slug in text
