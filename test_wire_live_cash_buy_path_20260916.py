#!/usr/bin/env python3
"""Hermetic: commercial.html + diagnostic.html first-screen Buy CTAs use the existing White Box hour PL."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WHITEBOX = "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07"
WHITEBOX_RAIL = "buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07"
AUTOPSY_RAIL = "buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g"
PAGES = (
    ("commercial.html", "commercial_hero"),
    ("diagnostic.html", "diagnostic_hero"),
)


class WireLiveCashBuyPathTests(unittest.TestCase):
    def test_first_screen_cta_is_existing_whitebox_hour(self) -> None:
        for name, utm in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                header = text.split("<header", 1)[1].split("</header>", 1)[0]
                after = text.split("</header>", 1)[1]
                self.assertIn(WHITEBOX, header)
                self.assertIn('class="cta"', header)
                self.assertIn("data-checkout", header)
                self.assertIn("Buy one White Box hour — $250", header)
                self.assertIn("utm_content=" + utm, header)
                self.assertNotIn("js-checkout-slot", text)
                self.assertNotIn("titanmcp-pad-pointer", header)
                self.assertIn('id="titanmcp-pad-pointer"', after)
                self.assertLess(text.find("data-checkout"), text.find('id="say"'))
                buy_line = next(ln for ln in header.splitlines() if "data-checkout" in ln)
                self.assertNotIn("$12,000", buy_line)
                self.assertNotIn("$30,000", buy_line)
                rails = set(re.findall(r"buy\.stripe\.com/[A-Za-z0-9]+", text))
                allowed = {WHITEBOX_RAIL}
                if name == "commercial.html":
                    allowed.add(AUTOPSY_RAIL)
                    self.assertIn(AUTOPSY_RAIL, text)
                else:
                    self.assertNotIn(AUTOPSY_RAIL, text)
                self.assertTrue(rails <= allowed, rails)


if __name__ == "__main__":
    unittest.main()
