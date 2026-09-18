"""Hermetic: tip-shelf $199 pages link after-fit $2500 to production_survival."""
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = [
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
]

def test_tipshelf_afterfit_upsell():
    for name in PAGES:
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "revenue/production_survival/README.md" in text, name
