#!/usr/bin/env python3
"""$199 diagnostic pages must expose Autopsy-style after-pay receipt→handoff."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = [
    ("dealer-service-lead-rescue.html", "https://buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b"),
    ("referral-intake-completeness.html", "https://buy.stripe.com/9B600i98N77b9uFeBk43S0c"),
    ("plant-downtime-handoff.html", "https://buy.stripe.com/14AfZgckZ0IN0Y99h043S0e"),
    ("repair-booking-preflight.html", "https://buy.stripe.com/9B66oGacR2QVdKVeBk43S0d"),
]


def test_diag_postpay_receipt_handoff() -> None:
    for name, plink in PAGES:
        text = (ROOT / name).read_text(encoding="utf-8")
        assert 'data-postpay-handoff="1"' in text, name
        assert "After purchase" in text, name
        assert "Stripe receipt" in text, name
        assert "mailto:tokenjunkielabs@gmail.com" in text, name
        assert plink in text, name


if __name__ == "__main__":
    test_diag_postpay_receipt_handoff()
    print("ok")
