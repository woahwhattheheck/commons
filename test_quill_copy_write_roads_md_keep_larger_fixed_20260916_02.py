"""quill-copy-write-roads-md-keep-larger-fixed-20260916-02 — KEEP Larger-fixed on Quill copy/write-roads MD doors."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

GROUND_PAGES = (
    ROOT / "ground" / "copy-paste-manufacturing.md",
    ROOT / "ground" / "LISTING_REGISTRY.md",
    ROOT / "ground" / "TERMINAL_CATALOG.md",
)

TOKEN_PAGES = (
    ROOT / "ground" / "tokens" / "write-roads.md",
    ROOT / "ground" / "tokens" / "distribution.md",
    ROOT / "ground" / "tokens" / "offer.md",
)


class TestQuillCopyWriteRoadsMdKeepLargerFixed2026091602(unittest.TestCase):
    def test_ground_pages_keep_autopsy_and_larger(self):
        for page in GROUND_PAGES:
            with self.subTest(page=str(page.relative_to(ROOT))):
                text = page.read_text(encoding="utf-8")
                self.assertRegex(text, r"## Live cash")

                self.assertIn("$199", text)
                self.assertIn("Larger fixed engagements", text)
                self.assertIn("diagnostic.html", text)
                self.assertIn("commercial.html", text)
                self.assertIn("$12,000", text)
                self.assertIn("$30,000", text)
                self.assertIn("../diagnostic.html", text)
                self.assertIn("../commercial.html", text)
                self.assertNotIn("buy.stripe.com", text)

    def test_token_pages_keep_autopsy_and_larger(self):
        for page in TOKEN_PAGES:
            with self.subTest(page=str(page.relative_to(ROOT))):
                text = page.read_text(encoding="utf-8")
                self.assertRegex(text, r"## Live cash")

                self.assertIn("$199", text)
                self.assertIn("Larger fixed engagements", text)
                self.assertIn("diagnostic.html", text)
                self.assertIn("commercial.html", text)
                self.assertIn("$12,000", text)
                self.assertIn("$30,000", text)
                self.assertIn("../../diagnostic.html", text)
                self.assertIn("../../commercial.html", text)
                self.assertNotIn("buy.stripe.com", text)

    def test_product_pages_exist(self):
        for name in ("diagnostic.html", "commercial.html"):
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
