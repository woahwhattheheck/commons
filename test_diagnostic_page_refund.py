"""Buyer pages surface the contract refund / miss remedy."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
REFUND = (
    "If the accepted diagnostic is not delivered inside the one-business-day window, "
    "the paid diagnostic amount is refunded unless the buyer elects in writing to receive "
    "one free next-business-day repair instead."
)
PAGES = [
    "dealer-service-lead-rescue.html",
    "plant-downtime-handoff.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
]


class DiagnosticPageRefundTests(unittest.TestCase):
    def test_four_diagnostic_pages_show_miss_remedy(self):
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                self.assertIn(REFUND, text)
                self.assertIn("Miss remedy", text)


if __name__ == "__main__":
    unittest.main()
