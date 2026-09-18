#!/usr/bin/env python3
"""Hermetic: compression + swarm/world/data Live cash."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['glyphs.html', 'program.html', 'accordion.html', 'breath.html', 'foldbook.html', 'loop.html', 'flipbook.html', 'swarm.html', 'world.html', 'data.html']
REQUIRED = ['id="live-cash"', "./dealer-service-lead-rescue.html", "./referral-intake-completeness.html", "./repair-booking-preflight.html", "./plant-downtime-handoff.html", "$199 dealer diagnostic"]
class LatchCompressionDoorsLiveCashTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text, f"{name} missing {n}")
                # Convert shelves reuse existing live buys; Live cash
                # product-page doors stay relative.
                live_cash = text.split('id="live-cash"', 1)[1].split("</section>", 1)[0]
                self.assertNotIn("buy.stripe.com", live_cash)
                self.assertNotIn("tools-cash.html", text)
if __name__ == "__main__":
    unittest.main()
