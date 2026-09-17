#!/usr/bin/env python3
"""Hermetic: wakeup.html Live cash surfaces Autopsy $29 + four $199 tip-shelf doors."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WAKE = ROOT / "wakeup.html"


class BlinkWakeupLiveCashTest(unittest.TestCase):
    def test_live_cash(self) -> None:
        text = WAKE.read_text(encoding="utf-8")
        self.assertIn('id="live-cash"', text)
        self.assertIn("agent-rescue.html", text)
        self.assertIn("$29", text)
        self.assertIn("dealer-service-lead-rescue.html", text)
        self.assertIn("referral-intake-completeness.html", text)
        self.assertIn("repair-booking-preflight.html", text)
        self.assertIn("plant-downtime-handoff.html", text)
        self.assertIn("$199", text)
        live_cash = text.split('id="live-cash"', 1)[1].split("</section>", 1)[0]
        self.assertNotIn("buy.stripe.com", live_cash)
        self.assertNotIn("donate.stripe.com", text)
        self.assertIn("https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g", text)
        self.assertIn("https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07", text)


if __name__ == "__main__":
    unittest.main()
