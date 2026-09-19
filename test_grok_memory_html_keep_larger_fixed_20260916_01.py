"""grok-memory-html-keep-larger-fixed-20260916-01 — KEEP Larger-fixed on memory remint."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "grok-memory-html-keep-larger-fixed-20260916-01"
PRODUCTS = [
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
]
LARGER = ("diagnostic.html", "commercial.html")
MEMORY_HTML = [
    "memory/index.html",
    "memory/ASTRA.html",
    "memory/CODEX_SOL.html",
    "memory/CURSOR_GROK.html",
    "memory/DOOR.html",
    "memory/JOJO.html",
    "memory/KITE.html",
    "memory/PLAYER2.html",
    "memory/PLUMB.html",
    "memory/RIDGE.html",
    "memory/RIVET.html",
    "memory/SOLDER.html",
    "memory/SPEC_DADDY.html",
]


class TestGrokMemoryHtmlKeepLargerFixed2026091601(unittest.TestCase):
    def test_constant_has_nested_autopsy_and_larger(self):
        sys.path.insert(0, str(ROOT))
        import memory_board
        html = memory_board.MEMORY_LIVE_CASH_HTML
        self.assertIn('id="live-cash"', html)


        self.assertIn("Larger fixed engagements", html)
        self.assertIn("../diagnostic.html", html)
        self.assertIn("../commercial.html", html)
        self.assertIn("$12,000", html)
        self.assertIn("$30,000", html)
        self.assertNotIn("buy.stripe.com", html)
        self.assertIn('href="../diagnostic.html"', html)
        self.assertIn('href="../commercial.html"', html)

    def test_tip_memory_html_has_autopsy_and_larger(self):
        for rel in MEMORY_HTML:
            path = ROOT / rel
            self.assertTrue(path.is_file(), rel)
            html = path.read_text(encoding="utf-8")
            self.assertIn('id="live-cash"', html, rel)


            self.assertIn("Larger fixed engagements", html, rel)
            self.assertIn("../diagnostic.html", html, rel)
            self.assertIn("../commercial.html", html, rel)
            self.assertNotIn("buy.stripe.com", html, rel)

    def test_product_pages_exist(self):
        for name in PRODUCTS + list(LARGER):
            self.assertTrue((ROOT / name).is_file(), name)

    def test_memory_board_remint_keeps_larger_fixed(self):
        sys.path.insert(0, str(ROOT))
        import memory_board

        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "memory").mkdir(parents=True)
        written = {}

        def write(path, text):
            written[os.path.basename(path)] = text
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(text, encoding="utf-8")

        memory_board.rebuild(
            str(root),
            rows=[],
            write=write,
            asset_v="test",
            doors_html="<nav>doors</nav>",
        )
        html = written.get("index.html") or (root / "memory" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="live-cash"', html)


        self.assertIn("Larger fixed engagements", html)
        self.assertIn("../diagnostic.html", html)
        self.assertIn("../commercial.html", html)
        self.assertNotIn("buy.stripe.com", html)

        page = memory_board._page("t", "<p>body</p>", "v", "<nav>doors</nav>")
        self.assertIn("Larger fixed engagements", page)
        self.assertIn("../diagnostic.html", page)
        self.assertNotIn("buy.stripe.com", page)


if __name__ == "__main__":
    unittest.main()
