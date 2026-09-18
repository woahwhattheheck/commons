"""grok-open-work-human-keep-larger-fixed-20260916-01 — KEEP live-cash+Larger on listing remint."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class TestGrokOpenWorkHumanKeepLargerFixed2026091601(unittest.TestCase):
    def test_tip_listing_has_autopsy_and_larger(self):
        text = (ROOT / "ground" / "open-work-structured-ids-on-current-main.md").read_text(encoding="utf-8")
        self.assertIn("## Live cash", text)
        self.assertIn("../dealer-service-lead-rescue.html", text)
        self.assertIn("Larger fixed engagements", text)
        self.assertIn("../diagnostic.html", text)
        self.assertIn("../commercial.html", text)
        self.assertIn("spy-ground-batch-live-cash-20260909-24", text)
        self.assertNotIn("buy.stripe.com", text)

    def test_render_human_keeps_live_cash_and_larger(self):
        sys.path.insert(0, str(ROOT))
        from host.open_work import render_human
        html = render_human({"main_sha": "deadbeef", "counts": {}, "items": []})
        self.assertIn("## Live cash", html)
        self.assertIn("../dealer-service-lead-rescue.html", html)
        self.assertIn("Larger fixed engagements", html)
        self.assertIn("../diagnostic.html", html)
        self.assertIn("../commercial.html", html)
        self.assertNotIn("buy.stripe.com", html)

    def test_product_pages_exist(self):
        for name in ("diagnostic.html", "commercial.html"):
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
