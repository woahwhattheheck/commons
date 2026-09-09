"""Tip docs/TITAN_HANDS_PEERS.md surfaces live Autopsy + $199 cash doors."""
from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
DOC = ROOT / "docs" / "TITAN_HANDS_PEERS.md"


class StampDocsTitanHandsPeersLiveCashTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = DOC.read_text(encoding="utf-8")

    def test_live_cash_section_exists(self):
        self.assertIn("## Live cash", self.text)

    def test_autopsy_29_on_agent_rescue(self):
        self.assertIn("$29", self.text)
        self.assertIn("Autopsy", self.text)
        self.assertIn("agent-rescue.html", self.text)

    def test_four_199_product_doors(self):
        for path in (
            "dealer-service-lead-rescue.html",
            "referral-intake-completeness.html",
            "repair-booking-preflight.html",
            "plant-downtime-handoff.html",
        ):
            self.assertIn(path, self.text)
        self.assertIn("$199", self.text)

    def test_no_invented_stripe_urls(self):
        self.assertNotIn("buy.stripe.com", self.text)
        self.assertNotIn("donate.stripe.com", self.text)


if __name__ == "__main__":
    unittest.main()
