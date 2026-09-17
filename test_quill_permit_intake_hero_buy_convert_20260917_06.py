#!/usr/bin/env python3
"""Hermetic: permit-intake tip hero is h1 → lede → offer/price → attested Buy before titanmcp."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "permit-intake-receipt.html"
PLINK = "https://buy.stripe.com/8x2cN42Kp8bf8qBgJs43S0n"


class PermitIntakeHeroBuyConvertTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PAGE.read_text(encoding="utf-8")

    def test_attested_permit_plink_only_no_invent(self):
        hrefs = re.findall(
            r'href="(https://buy\.stripe\.com/[A-Za-z0-9]+)"',
            self.page,
        )
        self.assertEqual(hrefs, [PLINK, PLINK])
        self.assertIn('class="buy"', self.page)
        self.assertIn("Start the $199 diagnostic", self.page)

    def test_hero_order_h1_lede_offer_buy_before_titanmcp(self):
        h1 = self.page.find("<h1>")
        lede = self.page.find('class="lede"')
        offer = self.page.find('class="offer"')
        buy = self.page.find(PLINK)
        titan = self.page.find('id="titanmcp-pad-pointer"')
        self.assertGreater(h1, 0)
        self.assertGreater(lede, h1)
        self.assertGreater(offer, lede)
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

    def test_truth_boundary_and_demo_kept(self):
        self.assertIn("Truth boundary", self.page)
        self.assertIn("Synthetic application", self.page)
        self.assertIn("Exact buyer intake", self.page)


if __name__ == "__main__":
    unittest.main()
