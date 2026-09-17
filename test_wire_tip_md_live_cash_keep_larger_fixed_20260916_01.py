"""wire-tip-md-live-cash-keep-larger-fixed-20260916-01 — KEEP Larger-fixed on tip MD doors."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGES = (
    "play-inhabit.md",
    "owner-context.md",
    "window-miss.md",
    "mirror-writeback.md",
    "ship-loop-prompt.md",
)
PRODUCTS = (
    "agent-rescue.html",
    "diagnostic.html",
    "commercial.html",
)


class TestWireTipMdLiveCashKeepLargerFixed2026091601(unittest.TestCase):
    def test_tip_md_batch_has_autopsy_and_larger(self):
        for rel in PAGES:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("## Live cash", text, rel)
            self.assertIn("./agent-rescue.html", text, rel)
            self.assertIn("$29", text, rel)
            self.assertIn("$199", text, rel)
            self.assertIn("Larger fixed engagements", text, rel)
            self.assertIn("./diagnostic.html", text, rel)
            self.assertIn("./commercial.html", text, rel)
            self.assertIn("$12,000", text, rel)
            self.assertIn("$30,000", text, rel)
            cash = text[text.find("## Live cash") :]
            self.assertNotIn("buy.stripe.com", cash, rel)

    def test_product_pages_exist(self):
        for name in PRODUCTS:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_did_not_touch_leftover_census_or_occupancy_batch(self):
        census = (ROOT / "leftover-census.md").read_text(encoding="utf-8")
        self.assertIn("<!-- leftover-id-census:begin -->", census)
        occ = (ROOT / "occupancy.md").read_text(encoding="utf-8")
        self.assertIn("Larger fixed engagements", occ)


if __name__ == "__main__":
    unittest.main()
