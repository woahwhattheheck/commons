#!/usr/bin/env python3
"""KEEP vs SELL is a live boards catalog door, so the landing hub must surface it.

boards.html / hub_pages.rebuild_boards() already project keep-sell.html after
payment-capability.html. test_door_hub.js requires every cataloged HTML door on
the runtime door.js tabs and the no-JS index.html hub. This regression pins that
parity without freezing leftover unique-pack bytes.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HREF = "keep-sell.html"
LABEL = "KEEP vs SELL"
DOOR_ENTRY = '["keep-sell.html", "KEEP vs SELL"]'
PAY_ENTRY = '["payment-capability.html", "payment rails"]'
ORCH_ENTRY = '["orchestration.html", "orchestration"]'
INDEX_KEEP = '<a class="door-btn" href="./keep-sell.html">KEEP vs SELL</a>'
INDEX_PAY = '<a class="door-btn" href="./payment-capability.html">payment rails</a>'
INDEX_ORCH = '<a class="door-btn" href="./orchestration.html">orchestration</a>'


class KeepSellDoorHubTests(unittest.TestCase):
    def test_door_js_use_tab_includes_keep_sell_after_payment_rails(self) -> None:
        text = (ROOT / "door.js").read_text(encoding="utf-8")
        self.assertEqual(text.count(DOOR_ENTRY), 1)
        self.assertLess(text.index(PAY_ENTRY), text.index(DOOR_ENTRY))
        self.assertLess(text.index(DOOR_ENTRY), text.index(ORCH_ENTRY))

    def test_index_static_hub_matches_keep_sell_order(self) -> None:
        text = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertEqual(text.count(INDEX_KEEP), 1)
        self.assertLess(text.index(INDEX_PAY), text.index(INDEX_KEEP))
        self.assertLess(text.index(INDEX_KEEP), text.index(INDEX_ORCH))

    def test_keep_sell_page_returns_home(self) -> None:
        text = (ROOT / HREF).read_text(encoding="utf-8")
        self.assertIn('href="./index.html"', text)
        self.assertIn(LABEL, text)


if __name__ == "__main__":
    unittest.main()
