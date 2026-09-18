"""grok-open-work-md-keep-larger-fixed-20260916-01 — KEEP Larger-fixed on OPEN_WORK remint."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class TestGrokOpenWorkMdKeepLargerFixed2026091601(unittest.TestCase):
    def test_tip_open_work_has_autopsy_and_larger(self):
        text = (ROOT / "ground" / "OPEN_WORK.md").read_text(encoding="utf-8")
        self.assertIn("## Live cash", text)
        self.assertIn("../agent-rescue.html", text)
        self.assertIn("Larger fixed engagements", text)
        self.assertIn("../diagnostic.html", text)
        self.assertIn("../commercial.html", text)
        self.assertIn("spy-ground-batch-live-cash-20260905-19", text)
        self.assertNotIn("buy.stripe.com", text)

    def test_render_pointer_keeps_larger_fixed(self):
        sys.path.insert(0, str(ROOT))
        from host.open_work import render_pointer
        html = render_pointer({"main_sha": "deadbeef"})
        self.assertIn("## Live cash", html)
        self.assertIn("../agent-rescue.html", html)
        self.assertIn("Larger fixed engagements", html)
        self.assertIn("../diagnostic.html", html)
        self.assertIn("../commercial.html", html)
        self.assertNotIn("buy.stripe.com", html)

    def test_product_pages_exist(self):
        for name in ("agent-rescue.html", "diagnostic.html", "commercial.html"):
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
