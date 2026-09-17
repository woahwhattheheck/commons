"""wire-ground-fleet-hub-md-keep-larger-fixed-20260916-01"""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = (
    "ground/CUSTOMER_LINK_BOUNDARY.md",
    "ground/DEVICE_CHURN.md",
    "ground/DEVICE_PATH_CENSUS.md",
    "ground/DEVICE_QUEUE_CAP.md",
    "ground/FLEET.md",
    "ground/HUB.md",
    "ground/HUB_TICK.md",
    "ground/INTERCONNECT.md",
    "ground/PIXEL_HEARTBEAT.md",
    "ground/WIRE_SUPER_MCP.md",
)
class T(unittest.TestCase):
    def test_batch(self):
        for rel in PAGES:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("../agent-rescue.html", text, rel)
            self.assertIn("Larger fixed engagements", text, rel)
            self.assertIn("../diagnostic.html", text, rel)
            self.assertIn("../commercial.html", text, rel)
            self.assertIn("$12,000", text, rel)
            self.assertIn("$30,000", text, rel)
    def test_products(self):
        for n in ("diagnostic.html","commercial.html","agent-rescue.html"):
            self.assertTrue((ROOT/n).is_file(), n)
if __name__ == "__main__":
    unittest.main()
