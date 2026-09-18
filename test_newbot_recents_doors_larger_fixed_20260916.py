#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOORS = [
    "recents.html",
    "ringdelta.html",
    "salvage.html",
    "shots.html",
    "slack-tags.html",
    "stealable-lanes.html",
    "stringmail.html",
    "swarm-dc.html",
    "swarm.html",
]


class NewbotRecentsLargerFixedBatchTest(unittest.TestCase):
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
        receipt = ROOT / "p" / "newbot-recents-doors-larger-fixed-20260916-02.md"
        self.assertTrue(receipt.is_file(), str(receipt))
        body = receipt.read_text(encoding="utf-8")
        self.assertIn("newbot-recents-doors-larger-fixed-20260916-02", body)


if __name__ == "__main__":
    unittest.main()
