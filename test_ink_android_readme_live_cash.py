"""Hermetic: android/README.md surfaces live Autopsy + $199 product doors."""

from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
README = ROOT / "android" / "README.md"

PRODUCT_MARKERS = (
    "../agent-rescue.html",
    "../dealer-service-lead-rescue.html",
    "../referral-intake-completeness.html",
    "../repair-booking-preflight.html",
    "../plant-downtime-handoff.html",
)


class TestInkAndroidReadmeLiveCash(unittest.TestCase):
    def test_live_cash_product_doors(self) -> None:
        text = README.read_text(encoding="utf-8")
        self.assertIn("## Live cash", text)
        for marker in PRODUCT_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("donate.stripe.com", text)


if __name__ == "__main__":
    unittest.main()
