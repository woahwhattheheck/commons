#!/usr/bin/env python3
"""Hermetic: observability/UI doors Live cash."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ["visual.html","look.html","shots.html","face.html","mirrors.html","avatars.html","nojs.html","reply.html"]
REQUIRED = ['id="live-cash"', "./agent-rescue.html", "./dealer-service-lead-rescue.html", "./referral-intake-completeness.html", "./repair-booking-preflight.html", "./plant-downtime-handoff.html", "$29 Autopsy", "$199 dealer diagnostic"]
class LatchObsDoorsLiveCashTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text, f"{name} missing {n}")
                self.assertNotIn("buy.stripe.com", text)
                self.assertNotIn("tools-cash.html", text)
if __name__ == "__main__":
    unittest.main()
