#!/usr/bin/env python3
"""Hermetic: agent-autopsy-intake tip hero is h1 → lead → $29 Buy (attested PL in hero)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "agent-autopsy-intake.html"
PLINK = "https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g"


class AgentAutopsyIntakeHeroBuyConvertTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PAGE.read_text(encoding="utf-8")
        hs = cls.page.find("<header")
        he = cls.page.find("</header>")
        cls.hero = cls.page[hs:he]

    def test_attested_autopsy_plink_only_no_invent(self):
        hrefs = re.findall(
            r'href="(https://buy\.stripe\.com/[A-Za-z0-9]+)',
            self.page,
        )
        self.assertTrue(hrefs)
        self.assertEqual(set(hrefs), {PLINK})
        self.assertGreaterEqual(hrefs.count(PLINK), 2)
        self.assertIn("Buy Agent Failure Autopsy — $29", self.page)
        self.assertIn('data-checkout', self.page)

    def test_hero_order_h1_lead_buy(self):
        h1 = self.hero.find("<h1")
        lead = self.hero.find('class="lead"')
        buy = self.hero.find(PLINK)
        price = self.hero.find('class="price"')
        self.assertGreater(h1, 0)
        self.assertGreater(lead, h1)
        self.assertGreater(price, lead)
        self.assertGreater(buy, price)
        self.assertIn("$29", self.hero[price : buy + 80])
        self.assertIn("Buy Agent Failure Autopsy — $29", self.hero)
        self.assertNotIn('id="titanmcp-pad-pointer"', self.hero)

    def test_buy_in_hero_before_grid_and_titanmcp(self):
        header_end = self.page.find("</header>")
        grid = self.page.find('class="grid"')
        buy_hero = self.page.find(PLINK)
        titan = self.page.find('id="titanmcp-pad-pointer"')
        self.assertGreater(header_end, 0)
        self.assertGreater(grid, header_end)
        self.assertLess(buy_hero, header_end)
        self.assertLess(buy_hero, grid)
        self.assertGreater(titan, header_end)
        self.assertGreater(titan, buy_hero)

    def test_offer_copy_and_truth_kept(self):
        self.assertIn("Turn the failure into a clean case brief.", self.page)
        self.assertIn("Ready for the Autopsy?", self.page)
        self.assertIn("does not invent a checkout URL", self.page)
        self.assertIn("utm_content=hero", self.page)
        self.assertIn("utm_content=ready_case_brief", self.page)
        self.assertIn("Local by construction", self.page)
        self.assertEqual(self.page.count('id="titanmcp-pad-pointer"'), 1)


if __name__ == "__main__":
    unittest.main()
