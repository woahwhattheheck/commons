"""quill-copy-md-keep-larger-fixed-20260916-01 — KEEP Larger-fixed on Quill copy/receipt MD doors."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PAGES = (
    ROOT / "ground" / "AUTHORSHIP.md",
    ROOT / "ground" / "COMMERCE.md",
    ROOT / "ground" / "DISTRIBUTION.md",
    ROOT / "ground" / "SALON.md",
    ROOT / "ground" / "BOOKS.md",
    ROOT / "ground" / "ANNEX.md",
    ROOT / "ground" / "WRITE-NOW.md",
    ROOT / "door" / "README.md",
    ROOT / "lda" / "AUTHORSHIP.md",
)


class TestQuillCopyMdKeepLargerFixed2026091601(unittest.TestCase):
    def test_pages_keep_autopsy_and_larger(self):
        for page in PAGES:
            with self.subTest(page=str(page.relative_to(ROOT))):
                text = page.read_text(encoding="utf-8")
                self.assertRegex(text, r"## Live cash")

                self.assertIn("$199", text)
                # Larger fixed shelf additive KEEP
                self.assertIn("Larger fixed engagements", text)
                self.assertIn("diagnostic.html", text)
                self.assertIn("commercial.html", text)
                self.assertIn("$12,000", text)
                self.assertIn("$30,000", text)
                self.assertIn("../diagnostic.html", text)
                self.assertIn("../commercial.html", text)
                self.assertNotIn("buy.stripe.com", text)

    def test_product_pages_exist(self):
        for name in ("diagnostic.html", "commercial.html"):
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
