#!/usr/bin/env python3
"""Hermetic: salesforce-contact tip hero is h1 → lead → $199 Buy before titanmcp."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "salesforce-contact-preflight.html"
PLINK = "https://buy.stripe.com/4gM8wO4SxbnrdKV9h043S0m"


class SalesforceContactHeroBuyConvertTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PAGE.read_text(encoding="utf-8")

    def test_attested_salesforce_plink_only_no_invent(self):
        hrefs = re.findall(
            r'href="(https://buy\.stripe\.com/[A-Za-z0-9]+)"',
            self.page,
        )
        self.assertEqual(hrefs, [PLINK, PLINK])
        self.assertIn("Start the $199 diagnostic", self.page)
        self.assertIn('class="price-actions"', self.page)
        self.assertIn('class="buy"', self.page)

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
        actions = self.page.find('class="price-actions"')
        self.assertGreater(actions, h1)
        self.assertGreater(buy, actions)
        window = self.page[actions:titan]
        self.assertIn("$199", window)
        self.assertIn("Start the $199 diagnostic", window)

    def test_titanmcp_pointer_kept_once_after_buy(self):
        self.assertEqual(self.page.count('id="titanmcp-pad-pointer"'), 1)
        self.assertIn("titanmcp 1.4.5", self.page)
        self.assertIn('href="./titanmcp.html"', self.page)

    def test_postpay_live_cash_and_demo_kept(self):
        self.assertIn('data-postpay-handoff="1"', self.page)
        self.assertIn('id="live-cash"', self.page)
        self.assertIn("Run preflight", self.page)
        self.assertIn("SalesforceContactPreflight", self.page)
        self.assertIn('class="foot-cta"', self.page)


if __name__ == "__main__":
    unittest.main()
