"""newbot-stealable-lanes-html-keep-larger-fixed-20260916-18 — KEEP Larger fixed on stealable remint."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "newbot-stealable-lanes-html-keep-larger-fixed-20260916-18"
PRODUCTS = [
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
]
LARGER = ("diagnostic.html", "commercial.html")
CASH_RE = re.compile(r'<section id="live-cash">.*?</section>', re.S)


class TestNewbotStealableLanesHtmlKeepLargerFixed2026091618(unittest.TestCase):
    def test_tip_stealable_has_autopsy_and_larger(self):
        html = (ROOT / "stealable-lanes.html").read_text(encoding="utf-8")
        self.assertIn('id="live-cash"', html)


        self.assertIn("Larger fixed engagements", html)
        for path in LARGER:
            self.assertIn(path, html)
        self.assertNotIn("buy.stripe.com", CASH_RE.search(html).group(0))

    def test_product_pages_exist(self):
        for name in PRODUCTS + list(LARGER):
            self.assertTrue((ROOT / name).is_file(), name)

    def test_render_html_keeps_larger_and_matches_tip_cash(self):
        import sys

        sys.path.insert(0, str(ROOT))
        from host import stealable_lanes as mod

        html = mod.render_html()
        self.assertIn("Larger fixed engagements", html)
        self.assertIn("diagnostic.html", html)
        self.assertIn("commercial.html", html)

        tip = (ROOT / "stealable-lanes.html").read_text(encoding="utf-8")
        tip_cash = CASH_RE.search(tip)
        gen_cash = CASH_RE.search(html)
        self.assertIsNotNone(tip_cash)
        self.assertIsNotNone(gen_cash)
        self.assertEqual(gen_cash.group(0), tip_cash.group(0))
        self.assertNotIn("buy.stripe.com", gen_cash.group(0))
        self.assertIn("LIVE_CASH_HTML", (ROOT / "host/stealable_lanes.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
