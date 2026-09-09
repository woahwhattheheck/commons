"""Hermetic: four tip-shelf $199 pages crosslink Autopsy $29."""
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = [
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
]

def test_tipshelf_autopsy_crosslink():
    for name in PAGES:
        text = (ROOT / name).read_text(encoding="utf-8")
        assert 'href="./agent-rescue.html"' in text, name
        assert "Agent Failure Autopsy" in text, name
