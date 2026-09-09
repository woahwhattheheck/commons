"""Hermetic: commons-apk.html surfaces live Autopsy + $199 product doors."""

from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
HTML = ROOT / "commons-apk.html"

PRODUCT_HREFS = (
    "./agent-rescue.html",
    "./dealer-service-lead-rescue.html",
    "./referral-intake-completeness.html",
    "./repair-booking-preflight.html",
    "./plant-downtime-handoff.html",
)


class TestInkCommonsApkLiveCash(unittest.TestCase):
    def test_live_cash_product_doors(self) -> None:
        text = HTML.read_text(encoding="utf-8")
        self.assertIn("Live cash", text)
        self.assertIn('id="cash-doors"', text)
        for href in PRODUCT_HREFS:
            with self.subTest(href=href):
                self.assertIn(href, text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("donate.stripe.com", text)
        self.assertNotIn("tools-cash.html", text)


if __name__ == "__main__":
    unittest.main()
