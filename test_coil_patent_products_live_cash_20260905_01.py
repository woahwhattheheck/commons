#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
PAGE = Path(__file__).resolve().parent / "patent-products.html"
REQUIRED = ['id="live-cash"',"./agent-rescue.html","./dealer-service-lead-rescue.html","./referral-intake-completeness.html","./repair-booking-preflight.html","./plant-downtime-handoff.html","$29 Autopsy","$199 dealer diagnostic"]
class T(unittest.TestCase):
    def test(self):
        t=PAGE.read_text(encoding="utf-8")
        for n in REQUIRED: self.assertIn(n,t)
        cash = t.split('id="live-cash"', 1)[1].split("</section>", 1)[0]
        self.assertNotIn("buy.stripe.com", cash)
        self.assertNotIn("tools-cash.html", t)
if __name__=="__main__": unittest.main()
