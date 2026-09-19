"""newbot-opportunity-html-keep-larger-fixed-20260916-17 — KEEP Larger fixed on opportunity remints."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "newbot-opportunity-html-keep-larger-fixed-20260916-17"
PRODUCTS = [
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
]
LARGER = ("diagnostic.html", "commercial.html")
CASH_RE = re.compile(r'<section id="live-cash"[^>]*>.*?</section>', re.S)


class TestNewbotOpportunityHtmlKeepLargerFixed2026091617(unittest.TestCase):
    def test_tip_opportunity_and_proof_have_autopsy_and_larger(self):
        for name in ("opportunity.html", "proof-to-proposal.html"):
            html = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn('id="live-cash"', html)
            self.assertIn("dealer-service-lead-rescue.html", html)
            self.assertIn("$199", html)
            self.assertIn("Larger fixed engagements", html)
            for path in LARGER:
                self.assertIn(path, html)
            self.assertNotIn("buy.stripe.com", CASH_RE.search(html).group(0))

    def test_product_pages_exist(self):
        for name in PRODUCTS + list(LARGER):
            self.assertTrue((ROOT / name).is_file(), name)

    def test_render_templates_keep_larger_and_match_tip_cash_sections(self):
        import sys

        sys.path.insert(0, str(ROOT))
        from host import opportunity_registry as mod

        registry = json.loads(
            (ROOT / "revenue/ip/opportunity_registry.json").read_text(encoding="utf-8")
        )
        rendered = {
            "opportunity.html": mod.render_opportunity_html(registry),
            "proof-to-proposal.html": mod.render_proof_html(registry),
        }
        for name, html in rendered.items():
            self.assertIn("Larger fixed engagements", html, name)
            self.assertIn("diagnostic.html", html, name)
            self.assertIn("commercial.html", html, name)
            self.assertIn("dealer-service-lead-rescue.html", html, name)
            tip = (ROOT / name).read_text(encoding="utf-8")
            tip_cash = CASH_RE.search(tip)
            gen_cash = CASH_RE.search(html)
            self.assertIsNotNone(tip_cash, name)
            self.assertIsNotNone(gen_cash, name)
            self.assertEqual(gen_cash.group(0), tip_cash.group(0), name)
            self.assertNotIn("buy.stripe.com", gen_cash.group(0))


if __name__ == "__main__":
    unittest.main()
