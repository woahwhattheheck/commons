#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
PAGE = Path(__file__).resolve().parent / "business-packs.html"
REQUIRED = ['id="live-cash"',"./dealer-service-lead-rescue.html","./referral-intake-completeness.html","./repair-booking-preflight.html","./plant-downtime-handoff.html","$199 dealer diagnostic"]
class T(unittest.TestCase):
    def test(self):
        t=PAGE.read_text(encoding="utf-8")
        for n in REQUIRED: self.assertIn(n,t)
        self.assertIn('id="buy-now-live-checkout"', t)
        self.assertNotIn("tools-cash.html", t)
if __name__=="__main__": unittest.main()
