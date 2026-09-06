"""Hermetic: START.md Live cash names Autopsy $29 + tip-shelf diagnostics."""
from pathlib import Path
START = Path(__file__).resolve().parent / "START.md"

def test_start_has_live_cash_section():
    text = START.read_text(encoding="utf-8")
    assert "## Live cash" in text
    assert "[$29 Autopsy checkout](./agent-rescue.html)" in text
    for slug in (
        "dealer-service-lead-rescue.html",
        "referral-intake-completeness.html",
        "repair-booking-preflight.html",
        "plant-downtime-handoff.html",
    ):
        assert slug in text
