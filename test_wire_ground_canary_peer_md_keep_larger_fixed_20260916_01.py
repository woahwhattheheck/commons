"""wire-ground-canary-peer-md-keep-larger-fixed-20260916-01"""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = (
    "ground/WATCHDOG_CANARY.md",
    "ground/DEVICE_CANARY.md",
    "ground/DEVICE_PATH_CANARY.md",
    "ground/PEER_WAKE_BUS.md",
    "ground/OPPORTUNITY_REGISTRY.md",
    "ground/REVIEW_LANE.md",
    "ground/RENDER_CONTRACT.md",
    "ground/board-as-surface.md",
    "ground/POST_CURL.md",
    "ground/SCOPE_TO_DELIVERY.md",
)
class T(unittest.TestCase):
    def test_batch(self):
        for rel in PAGES:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("../agent-rescue.html", text, rel)
            self.assertIn("$199", text, rel)
            self.assertIn("Larger fixed engagements", text, rel)
            self.assertIn("../diagnostic.html", text, rel)
            self.assertIn("../commercial.html", text, rel)
            self.assertIn("$12,000", text, rel)
            self.assertIn("$30,000", text, rel)
            self.assertNotIn("buy.stripe.com", text[text.lower().find("live cash"):] if "live cash" in text.lower() else text, rel)
    def test_products(self):
        for name in ("diagnostic.html", "commercial.html"):
            self.assertTrue((ROOT / name).is_file(), name)
if __name__ == "__main__":
    unittest.main()
