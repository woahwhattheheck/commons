#!/usr/bin/env python3
"""wire-autopsy-x-storefront-20260917-01 — thin Autopsy storefront.

First-screen autopsy-buy.html with EXISTING live Stripe Payment Links only.
Tip KEEP. No remint. No invent Stripe. No login words. 337 NO.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "autopsy-buy.html"
RESCUE = ROOT / "agent-rescue.html"
RECEIPT = ROOT / "p" / "wire-autopsy-x-storefront-20260917-01.md"

AUTOPSY_PL = "https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g"
WHITEBOX_HOUR_PL = "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07"
BUY_HOST_PATH = re.compile(
    r"https?://buy\.stripe\.com/([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)


def live_buy_urls(html: str) -> set[str]:
    return {
        f"https://buy.stripe.com/{path}"
        for path in BUY_HOST_PATH.findall(html)
    }


class TestWireAutopsyXStorefront2026091701(unittest.TestCase):
    def test_storefront_is_thin_first_screen_with_existing_pls(self) -> None:
        html = PAGE.read_text(encoding="utf-8")
        self.assertIn("<h1>Agent Failure Autopsy — $29</h1>", html)
        self.assertIn(
            "One failed coding-agent run → evidence-linked causes + fix steps.",
            html,
        )
        self.assertIn("Buy Autopsy $29", html)
        self.assertIn("Buy one White Box hour $250", html)
        self.assertIn("./agent-rescue.html", html)
        self.assertIn('class="cta"', html)
        self.assertEqual(
            live_buy_urls(html),
            {AUTOPSY_PL, WHITEBOX_HOUR_PL},
        )
        self.assertIn(AUTOPSY_PL, html)
        self.assertIn(WHITEBOX_HOUR_PL, html)
        self.assertNotIn("donate.stripe.com", html)
        self.assertIsNone(re.search(r"\blogin\b", html, flags=re.I))
        # Primary CTA appears before secondary and before detail link.
        primary_at = html.find("Buy Autopsy $29")
        secondary_at = html.find("Buy one White Box hour $250")
        detail_at = html.find("./agent-rescue.html")
        self.assertGreater(primary_at, -1)
        self.assertGreater(secondary_at, primary_at)
        self.assertGreater(detail_at, primary_at)

    def test_agent_rescue_already_has_exact_autopsy_pl(self) -> None:
        html = RESCUE.read_text(encoding="utf-8")
        self.assertIn(AUTOPSY_PL, html)
        hrefs = re.findall(
            r'href="(https://buy\.stripe\.com/[A-Za-z0-9]+(?:\?[^"]*)?)"',
            html,
        )
        self.assertTrue(any(AUTOPSY_PL in href for href in hrefs))

    def test_receipt_cites_claim_and_existing_pls(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: wire-autopsy-x-storefront-20260917-01", text)
        self.assertIn("autopsy-buy.html", text)
        self.assertIn(AUTOPSY_PL, text)
        self.assertIn(WHITEBOX_HOUR_PL, text)
        self.assertIn("Tip KEEP", text)
        self.assertTrue(PAGE.is_file())
        self.assertTrue(RESCUE.is_file())


if __name__ == "__main__":
    unittest.main()