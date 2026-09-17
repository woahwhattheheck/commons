#!/usr/bin/env python3
"""Hermetic: webmcp.html Live cash — direct product doors on Shared Pad door."""
from __future__ import annotations
import re
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "webmcp.html"
REQUIRED = ['id="live-cash"', "./agent-rescue.html", "./dealer-service-lead-rescue.html", "./referral-intake-completeness.html", "./repair-booking-preflight.html", "./plant-downtime-handoff.html", "$29 Autopsy", "$199 dealer diagnostic"]
ALLOWED_LIVE_BUY_URLS = {
    "https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g",
    "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07",
}
BUY_HOST_PATH = re.compile(r"https?://buy\.stripe\.com/([A-Za-z0-9_-]+)", re.I)


class LatchWebmcpHtmlLiveCashTest(unittest.TestCase):
    def test_direct_product_doors(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        for needle in REQUIRED:
            self.assertIn(needle, text, f"missing {needle}")
        found = {
            "https://buy.stripe.com/%s" % path
            for path in BUY_HOST_PATH.findall(text)
        }
        self.assertEqual(found, ALLOWED_LIVE_BUY_URLS)
        self.assertNotIn("donate.stripe.com", text)
        self.assertNotIn("tools-cash.html", text)
        live_cash = text.split('id="live-cash"', 1)[1].split("</section>", 1)[0]
        self.assertNotIn("buy.stripe.com", live_cash)


if __name__ == "__main__":
    unittest.main()
