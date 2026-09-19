#!/usr/bin/env python3
"""Hermetic: pad.html Live cash — direct product doors."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "pad.html"

REQUIRED = [
    'id="live-cash"',
    "./dealer-service-lead-rescue.html",
    "./referral-intake-completeness.html",
    "./repair-booking-preflight.html",
    "./plant-downtime-handoff.html",
    "$199 dealer diagnostic",
]


class LatchPadHtmlLiveCashTest(unittest.TestCase):
    def test_direct_product_doors(self) -> None:
        self.assertTrue(PAGE.is_file(), "pad.html missing")
        text = PAGE.read_text(encoding="utf-8")
        for needle in REQUIRED:
            self.assertIn(needle, text, f"missing {needle}")
        # Convert shelf reuses existing live buys; Live cash product-page
        # doors stay relative (latch-job-pad-convert-shelf-20260917-01).
        live_cash = text.split('id="live-cash"', 1)[1].split("</section>", 1)[0]
        self.assertNotIn("buy.stripe.com", live_cash)
        self.assertNotIn("tools-cash.html", text)


if __name__ == "__main__":
    unittest.main()
