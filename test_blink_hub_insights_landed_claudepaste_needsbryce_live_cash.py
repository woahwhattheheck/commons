#!/usr/bin/env python3
"""Hermetic: hub-eyes/insights/landed-work/claude-paste/needs-bryce Live cash."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
FILES = ["hub-eyes.html","insights.html","landed-work.html","claude-paste.html","needs-bryce.html"]
class T(unittest.TestCase):
    def test_all(self) -> None:
        for name in FILES:
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn('id="live-cash"', text, name)
            self.assertIn("agent-rescue.html", text, name)
            self.assertIn("$29", text, name)
            self.assertIn("dealer-service-lead-rescue.html", text, name)
            self.assertIn("$199", text, name)
            # live-cash section must not invent Stripe URLs (claude-paste body may cite buy.stripe.com as owner law)
            section = text.split('id="live-cash"', 1)[1][:800]
            self.assertNotIn("buy.stripe.com", section, name)
            self.assertNotIn("donate.stripe.com", section, name)
if __name__ == "__main__":
    unittest.main()
