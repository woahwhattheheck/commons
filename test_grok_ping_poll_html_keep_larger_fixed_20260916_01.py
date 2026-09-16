"""grok-ping-poll-html-keep-larger-fixed-20260916-01 — KEEP Larger-fixed on ping/poll.html."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "ping" / "poll.html"


class TestGrokPingPollHtmlKeepLargerFixed2026091601(unittest.TestCase):
    def test_poll_html_has_autopsy_and_larger(self):
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="live-cash"', text)
        self.assertIn("../agent-rescue.html", text)
        self.assertIn("$29 Autopsy", text)
        self.assertIn("$199", text)
        self.assertIn("Larger fixed", text)
        self.assertIn("../diagnostic.html", text)
        self.assertIn("../commercial.html", text)
        self.assertIn("$12,000", text)
        self.assertIn("$30,000", text)
        cash_start = text.find('id="live-cash"')
        cash = text[cash_start:cash_start + 1200]
        self.assertNotIn("buy.stripe.com", cash)

    def test_product_pages_exist(self):
        for name in ("agent-rescue.html", "diagnostic.html", "commercial.html"):
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
