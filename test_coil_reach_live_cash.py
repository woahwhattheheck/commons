#!/usr/bin/env python3
"""Hermetic: reach.html Live cash — direct product doors (not tools-cash pointer)."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "reach.html"
REQUIRED = ['id="live-cash"',"./agent-rescue.html","./dealer-service-lead-rescue.html","./referral-intake-completeness.html","./repair-booking-preflight.html","./plant-downtime-handoff.html","$29 Autopsy","$199 dealer diagnostic"]
class T(unittest.TestCase):
    def test(self):
        t=PAGE.read_text(encoding="utf-8")
        for n in REQUIRED: self.assertIn(n,t)
        self.assertNotIn("buy.stripe.com", t)
        self.assertNotIn("tools-cash.html", t)
if __name__=="__main__": unittest.main()
