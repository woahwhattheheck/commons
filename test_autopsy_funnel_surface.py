#!/usr/bin/env python3
"""Assert index + commercial surface the live $29 Autopsy funnel (verified plink)."""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
COMMERCIAL = ROOT / "commercial.html"
PLINK = "buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g"
STALE = "Same-day proof starts at $2,500"


class AutopsyFunnelSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = INDEX.read_text(encoding="utf-8")
        cls.commercial = COMMERCIAL.read_text(encoding="utf-8")

    def test_index_leads_with_live_29_autopsy(self):
        self.assertIn("$29", self.index)
        self.assertIn("agent-rescue.html", self.index)
        self.assertIn(PLINK, self.index)
        offer = self.index.split('id="agent-failure-diagnostic-offer"', 1)[1].split("</section>", 1)[0]
        self.assertIn("Agent Failure Autopsy", offer)
        self.assertIn("./agent-rescue.html", offer)
        self.assertIn(PLINK, offer)
        self.assertIn("./agent-triage.html", offer)
        self.assertNotIn("A working $2,500 survival proof is the next step", offer)

    def test_commercial_points_at_29_not_stale_2500(self):
        self.assertIn("$29", self.commercial)
        self.assertIn("agent-rescue.html", self.commercial)
        self.assertIn(PLINK, self.commercial)
        self.assertNotIn(STALE, self.commercial)
        self.assertNotIn("same-day proof starts at $2,500", self.commercial.lower())
        self.assertNotIn("$2,500 same-day proof and $15,000 five-day recovery", self.commercial)
        self.assertIn("$30,000", self.commercial)


if __name__ == "__main__":
    unittest.main()
