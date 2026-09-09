"""Hermetic: ENTRY.md + entry.html Live cash Autopsy $29 + tip-shelf."""
from pathlib import Path
ROOT = Path(__file__).resolve().parent

def _check(text: str, autopsy_link: str):
    assert "## Live cash" in text or 'id="live-cash"' in text
    assert autopsy_link in text
    for slug in (
        "dealer-service-lead-rescue.html",
        "referral-intake-completeness.html",
        "repair-booking-preflight.html",
        "plant-downtime-handoff.html",
    ):
        assert slug in text

def test_entry_md_live_cash():
    _check((ROOT / "ENTRY.md").read_text(encoding="utf-8"), "[$29 Autopsy checkout](./agent-rescue.html)")

def test_entry_html_live_cash():
    _check((ROOT / "entry.html").read_text(encoding="utf-8"), 'href="./agent-rescue.html"')
