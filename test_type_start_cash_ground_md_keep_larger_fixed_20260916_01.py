"""type-start-cash-ground-md-keep-larger-fixed-20260916-01 — KEEP Larger on START + cash ground MD."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PATHS = (
    ("START.md", "./diagnostic.html", "./commercial.html", "./agent-rescue.html"),
    ("ground/CASH_NOW.md", "../diagnostic.html", "../commercial.html", "../agent-rescue.html"),
    ("ground/CHECKOUT_CAPABILITY.md", "../diagnostic.html", "../commercial.html", "../agent-rescue.html"),
    ("ground/BAZAAR.md", "../diagnostic.html", "../commercial.html", "../agent-rescue.html"),
    ("ground/BUSINESS_PACKS.md", "../diagnostic.html", "../commercial.html", "../agent-rescue.html"),
)


class TestTypeStartCashGroundMdKeepLargerFixed2026091601(unittest.TestCase):
    def test_tip_shelves_have_autopsy_and_larger(self):
        for rel, diag, comm, autopsy in PATHS:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("## Live cash", text, rel)
            self.assertIn(autopsy, text, rel)
            self.assertIn("Larger fixed engagements", text, rel)
            self.assertIn(diag, text, rel)
            self.assertIn(comm, text, rel)
            self.assertNotIn("buy.stripe.com", text, rel)

    def test_product_pages_exist(self):
        for name in ("agent-rescue.html", "diagnostic.html", "commercial.html"):
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
