"""quill-commerce-door-keep-larger-fixed-20260916-01 — KEEP Larger-fixed on commerce/door HTML."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PAGES = (
    ROOT / "commerce.html",
    ROOT / "distribution.html",
    ROOT / "door" / "index.html",
)


class TestQuillCommerceDoorKeepLargerFixed2026091601(unittest.TestCase):
    def test_pages_have_autopsy_and_larger(self):
        for page in PAGES:
            with self.subTest(page=page.name):
                text = page.read_text(encoding="utf-8")
                self.assertIn('id="live-cash"', text)
                self.assertIn("Autopsy", text)
                self.assertIn("$199", text)
                cash_start = text.find('id="live-cash"')
                cash = text[cash_start : cash_start + 900]
                self.assertIn("Larger fixed", cash)
                self.assertIn("diagnostic.html", cash)
                self.assertIn("commercial.html", cash)
                self.assertIn("$12,000", cash)
                self.assertIn("$30,000", cash)
                self.assertNotIn("buy.stripe.com", cash)

    def test_product_pages_exist(self):
        for name in ("agent-rescue.html", "diagnostic.html", "commercial.html"):
            self.assertTrue((ROOT / name).is_file(), name)

    def test_path_prefixes(self):
        commerce = (ROOT / "commerce.html").read_text(encoding="utf-8")
        door = (ROOT / "door" / "index.html").read_text(encoding="utf-8")
        c = commerce[commerce.find('id="live-cash"') : commerce.find('id="live-cash"') + 900]
        d = door[door.find('id="live-cash"') : door.find('id="live-cash"') + 900]
        self.assertIn("./diagnostic.html", c)
        self.assertIn("./commercial.html", c)
        self.assertIn("../diagnostic.html", d)
        self.assertIn("../commercial.html", d)


if __name__ == "__main__":
    unittest.main()
