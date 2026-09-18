#!/usr/bin/env python3
"""Hermetic: late-cancel-noshow tip hero is h1 → lead → $3,500 Buy (attested PL in hero)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "late-cancel-noshow-fee-leakage.html"
PLINK = "https://buy.stripe.com/14AfZg1Gl3UZ7mxfFo43S0x"


class LateCancelNoshowHeroBuyConvertTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PAGE.read_text(encoding="utf-8")
        hs = cls.page.find("<header")
        he = cls.page.find("</header>")
        cls.hero = cls.page[hs:he]

    def test_attested_late_cancel_plink_only_no_invent(self):
        hrefs = re.findall(
            r'href="(https://buy\.stripe\.com/[A-Za-z0-9]+)"',
            self.page,
        )
        self.assertTrue(hrefs)
        self.assertEqual(set(hrefs), {PLINK})
        self.assertGreaterEqual(hrefs.count(PLINK), 2)
        self.assertIn("Open verified Stripe checkout — $3,500", self.page)
        self.assertIn('class="cta"', self.page)

    def test_hero_order_h1_lead_buy(self):
        h1 = self.hero.find("<h1")
        lead = self.hero.find('class="lead"')
        buy = self.hero.find(PLINK)
        money = self.hero.find('class="money"')
        self.assertGreater(h1, 0)
        self.assertGreater(lead, h1)
        self.assertGreater(money, lead)
        self.assertGreater(buy, money)
        self.assertIn("$3,500", self.hero[money:buy + 80])
        self.assertIn("Open verified Stripe checkout — $3,500", self.hero)
        self.assertNotIn('id="titanmcp-pad-pointer"', self.hero)

    def test_buy_in_hero_before_grid_cards(self):
        header_end = self.page.find("</header>")
        grid = self.page.find('class="grid"')
        buy_hero = self.page.find(PLINK)
        self.assertGreater(header_end, 0)
        self.assertGreater(grid, header_end)
        self.assertLess(buy_hero, header_end)
        self.assertLess(buy_hero, grid)

    def test_offer_copy_and_truth_kept(self):
        self.assertIn("Late-Cancellation / No-Show Fee Leakage Diagnostic", self.page)
        self.assertIn("economic truth", self.page.lower())
        self.assertIn("≤500 appointments", self.page)
        self.assertIn("7 business days", self.page)
        self.assertIn("does not invent a checkout URL", self.page)


if __name__ == "__main__":
    unittest.main()
