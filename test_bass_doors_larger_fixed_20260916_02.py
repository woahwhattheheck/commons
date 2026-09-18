#!/usr/bin/env python3
from __future__ import annotations
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "commercial.json"
EXPECTED = [
    {
        "href": "./diagnostic.html",
        "label": "GGUF diagnostic · $12,000 / 10 days",
        "sku": "gguf-diagnostic-12000",
    },
    {
        "href": "./commercial.html",
        "label": "White Box pilot · $30,000 / 30 days",
        "sku": "white-box-pilot-30000",
    },
]


class BassLargerFixedBatch2Test(unittest.TestCase):
    def test_commercial_json_has_only_existing_larger_fixed_products(self) -> None:
        data = json.loads(TARGET.read_text(encoding="utf-8"))
        self.assertEqual(data["live_cash"]["larger_fixed"], EXPECTED)
        self.assertNotIn("buy.stripe.com", TARGET.read_text(encoding="utf-8"))

    def test_sibling_html_is_live_cash_and_was_not_reminted(self) -> None:
        html = (ROOT / "commercial.html").read_text(encoding="utf-8")
        self.assertRegex(html, re.compile(r"live\s*[- ]?cash", re.IGNORECASE))
        self.assertNotRegex(html, re.compile(r"larger fixed", re.IGNORECASE))


if __name__ == "__main__":
    unittest.main()
