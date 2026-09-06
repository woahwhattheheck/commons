#!/usr/bin/env python3
"""Hermetic: catalog/commons-slack/keyb/titanmcp/telegram Live cash doors."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
FILES = ["catalog.html","commons-slack.html","keyb.html","titanmcp.html","telegram.html"]
class T(unittest.TestCase):
    def test_all(self) -> None:
        for name in FILES:
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn('id="live-cash"', text, name)
            self.assertIn("agent-rescue.html", text, name)
            self.assertIn("$29", text, name)
            self.assertIn("dealer-service-lead-rescue.html", text, name)
            self.assertIn("referral-intake-completeness.html", text, name)
            self.assertIn("repair-booking-preflight.html", text, name)
            self.assertIn("plant-downtime-handoff.html", text, name)
            self.assertIn("$199", text, name)
            self.assertNotIn("buy.stripe.com", text, name)
if __name__ == "__main__":
    unittest.main()
