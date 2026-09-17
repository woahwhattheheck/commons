#!/usr/bin/env python3
"""Hermetic: owner-now-revenue.html Live cash direct doors."""
from __future__ import annotations
import unittest
from pathlib import Path
PAGE = Path(__file__).resolve().parent / "owner-now-revenue.html"
REQUIRED = ['id="live-cash"',"./agent-rescue.html","./dealer-service-lead-rescue.html","./referral-intake-completeness.html","./repair-booking-preflight.html","./plant-downtime-handoff.html","$29 Autopsy","$199 dealer diagnostic"]
class T(unittest.TestCase):
    def test(self):
        t=PAGE.read_text(encoding="utf-8")
        for n in REQUIRED: self.assertIn(n,t)
        self.assertNotIn("tools-cash.html", t)
        self.assertNotIn("https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g", t)
        self.assertIn("https://donate.stripe.com/fZucN40Ch9fj7mxgJs43S08", t)
if __name__=="__main__": unittest.main()
