#!/usr/bin/env python3
"""Hermetic: webmcp.html Live cash + live titanmcp pad pointer."""
from __future__ import annotations
import re
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "webmcp.html"
ALLOWED_LIVE_BUY_URLS = {
    "https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g",
    "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07",
}
BUY_HOST_PATH = re.compile(r"https?://buy\.stripe\.com/([A-Za-z0-9_-]+)", re.I)


class LatchWebmcpTitanmcpPointerTest(unittest.TestCase):
    def test_pointer_and_cash(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="titanmcp-pad-pointer"', text)
        self.assertIn("https://webmcp-pad.vercel.app/", text)
        self.assertIn("1.4.5", text)
        self.assertIn('id="live-cash"', text)
        self.assertIn("./agent-rescue.html", text)
        self.assertIn("$29 Autopsy", text)
        found = {
            "https://buy.stripe.com/%s" % path
            for path in BUY_HOST_PATH.findall(text)
        }
        self.assertEqual(found, ALLOWED_LIVE_BUY_URLS)
        live_cash = text.split('id="live-cash"', 1)[1].split("</section>", 1)[0]
        self.assertNotIn("buy.stripe.com", live_cash)


if __name__ == "__main__":
    unittest.main()
