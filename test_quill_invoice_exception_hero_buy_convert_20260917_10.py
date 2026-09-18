#!/usr/bin/env python3
"""Hermetic: invoice-exception tip hero is h1 → lead → $199 Buy before titanmcp."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "invoice-exception-pack.html"
PLINK = "https://buy.stripe.com/14A00i84Jdvz36hdxg43S0l"


class InvoiceExceptionHeroBuyConvertTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PAGE.read_text(encoding="utf-8")

    def test_attested_invoice_plink_only_no_invent(self):
        hrefs = re.findall(
            r'href="(https://buy\.stripe\.com/[A-Za-z0-9]+)"',
            self.page,
        )
        self.assertEqual(hrefs, [PLINK, PLINK, PLINK])
        self.assertIn("Start the $199 diagnostic", self.page)
        self.assertIn('class="cta"', self.page)
        self.assertIn('class="price"', self.page)

    def test_hero_order_h1_lead_buy_before_titanmcp(self):
        h1 = self.page.find("<h1>")
        lead = self.page.find('class="lead"')
        buy = self.page.find(PLINK)
        titan = self.page.find('id="titanmcp-pad-pointer"')
        self.assertGreater(h1, 0)
        self.assertGreater(lead, h1)
        self.assertGreater(buy, lead)
        self.assertGreater(titan, buy)
        between = self.page[h1:buy]
        self.assertNotIn('id="titanmcp-pad-pointer"', between)
        price = self.page.find('class="price"')
        self.assertGreater(price, h1)
        self.assertGreater(buy, price)
        window = self.page[price:titan]
        self.assertIn("$199", window)
        self.assertIn("Start the $199 diagnostic", window)

    def test_titanmcp_pointer_kept_once_after_buy(self):
        self.assertEqual(self.page.count('id="titanmcp-pad-pointer"'), 1)
        self.assertIn("titanmcp 1.4.5", self.page)
        self.assertIn('href="./titanmcp.html"', self.page)

    def test_demo_intake_noscript_and_live_cash_kept(self):
        self.assertIn('id="invoice-demo"', self.page)
        self.assertIn('id="buyer-intake"', self.page)
        self.assertIn("<noscript>", self.page)
        self.assertIn('id="live-cash"', self.page)
        self.assertIn("invoice-exception-pack-diagnostic", self.page)


if __name__ == "__main__":
    unittest.main()
