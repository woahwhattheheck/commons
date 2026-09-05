#!/usr/bin/env python3
"""Hermetic pin: Autopsy $29 card on commerce tip shelf."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMERCE = ROOT / "commerce.html"


class TestForgeAutopsyCommerceShelf(unittest.TestCase):
    def test_tip_shelf_surfaces_autopsy_29(self) -> None:
        raw = COMMERCE.read_text(encoding="utf-8")
        self.assertIn('id="sku-agent-failure-autopsy"', raw)
        self.assertIn("Agent Failure Autopsy", raw)
        self.assertIn("$29 once", raw)
        self.assertIn('href="./agent-rescue.html"', raw)
        self.assertIn("Open $29 Autopsy checkout", raw)
        # Do not invent a second plink on this page.
        self.assertNotIn("buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g", raw)


if __name__ == "__main__":
    unittest.main()
