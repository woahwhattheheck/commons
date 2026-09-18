"""quill-sitting-remint-md-keep-larger-fixed-20260916-09 — KEEP Larger-fixed on remint stripper."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PAGES = (ROOT / "ground" / "SITTING_REMINT.md",)


class TestQuillSittingRemintMdKeepLargerFixed2026091609(unittest.TestCase):
    def test_pages_keep_autopsy_and_larger(self):
        for page in PAGES:
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
                m = re.search(r"(?ms)^## Live cash\b.*?(?=^## |\Z)", text)
                self.assertIsNotNone(m, "Live cash section missing")
                live = m.group(0)
                self.assertIn("Larger fixed engagements", live)
                self.assertNotIn("buy.stripe.com", live)

    def test_product_pages_exist(self):
        for name in ("diagnostic.html", "commercial.html"):
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
