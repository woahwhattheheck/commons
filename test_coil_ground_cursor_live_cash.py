#!/usr/bin/env python3
"""Hermetic: ground/CURSOR.md Live cash section."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
DOC = ROOT / "ground" / "CURSOR.md"
REQUIRED = ["## Live cash","../agent-rescue.html","../dealer-service-lead-rescue.html","../referral-intake-completeness.html","../repair-booking-preflight.html","../plant-downtime-handoff.html","$29 Autopsy","$199 dealer diagnostic"]
class T(unittest.TestCase):
    def test(self):
        t=DOC.read_text(encoding="utf-8")
        for n in REQUIRED: self.assertIn(n,t)
        self.assertNotIn("buy.stripe.com", t)
if __name__=="__main__": unittest.main()
