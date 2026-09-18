#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOORS = [
    "since-you-last-looked.html",
    "subzero-proof.html",
    "subzero-quote.html",
    "subzero-receipt.html",
    "subzero.html",
    "super-mcp.html",
    "tabletop.html",
    "task-forge.html",
    "the-world.html",
    "titan-hands-free-sample.html",
    "toolbench.html",
    "topics.html",
]


class NewbotSinceLargerFixedBatchTest(unittest.TestCase):
    def test_larger_fixed_on_doors(self) -> None:
        for name in DOORS:
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("Larger fixed engagements", text, name)
            self.assertIn("diagnostic.html", text, name)
            self.assertIn("commercial.html", text, name)
            self.assertIn("$12,000", text, name)
            self.assertIn("$30,000", text, name)
            self.assertIn('id="live-cash"', text, name)

    def test_receipt_present(self) -> None:
        receipt = ROOT / "p" / "newbot-since-doors-larger-fixed-20260916-03.md"
        self.assertTrue(receipt.is_file(), str(receipt))
        body = receipt.read_text(encoding="utf-8")
        self.assertIn("newbot-since-doors-larger-fixed-20260916-03", body)


if __name__ == "__main__":
    unittest.main()
