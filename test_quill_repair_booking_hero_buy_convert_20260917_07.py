#!/usr/bin/env python3
"""Hermetic: repair-booking tip hero is h1 → lead → offer/price → attested Buy before titanmcp."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "repair-booking-preflight.html"
PLINK = "https://buy.stripe.com/9B66oGacR2QVdKVeBk43S0d"


class RepairBookingHeroBuyConvertTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PAGE.read_text(encoding="utf-8")

    def test_attested_repair_plink_only_no_invent(self):
        hrefs = re.findall(
            r'href="(https://buy\.stripe\.com/[A-Za-z0-9]+)"',
            self.page,
        )
        self.assertEqual(hrefs, [PLINK, PLINK])
        self.assertIn("Start the $199 diagnostic", self.page)
        self.assertIn('class="button primary"', self.page)

    def test_hero_order_h1_lead_offer_buy_before_titanmcp(self):
        h1 = self.page.find("<h1>")
        lead = self.page.find('class="lead"')
        offer = self.page.find('aria-label="Offer"')
        buy = self.page.find(PLINK)
        titan = self.page.find('id="titanmcp-pad-pointer"')
        self.assertGreater(h1, 0)
        self.assertGreater(lead, h1)
        self.assertGreater(offer, lead)
        self.assertGreater(buy, offer)
        self.assertGreater(titan, buy)
        between = self.page[h1:buy]
        self.assertNotIn('id="titanmcp-pad-pointer"', between)
        window = self.page[offer:buy]
        self.assertIn("$199", window)
        self.assertIn('class="price"', window)

    def test_titanmcp_pointer_kept_once_after_buy(self):
        self.assertEqual(self.page.count('id="titanmcp-pad-pointer"'), 1)
        self.assertIn("titanmcp 1.4.5", self.page)
        self.assertIn('href="./titanmcp.html"', self.page)

    def test_demo_and_foot_cta_kept(self):
        self.assertIn("Run the contract", self.page)
        self.assertIn("Synthetic-only public tool", self.page)
        self.assertIn('aria-label="Offer"', self.page)


if __name__ == "__main__":
    unittest.main()
