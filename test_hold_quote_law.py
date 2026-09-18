"""Hermetic: HOLD_QUOTE owner law is on tree with Bryce exact words."""
from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
QUOTE_SNIP = "quote a justification from my exact words"
LAW = ROOT / "ground" / "HOLD_QUOTE.md"
MEM = ROOT / "memory" / "HOLD_QUOTE.md"
RULE = ROOT / ".cursor" / "rules" / "hold-quote.mdc"
START = ROOT / "START.md"


class HoldQuoteLawTests(unittest.TestCase):
    def test_ground_card_has_bryce_quote(self) -> None:
        text = LAW.read_text(encoding="utf-8")
        self.assertIn(QUOTE_SNIP, text)
        self.assertIn("ignore holds", text.lower())

    def test_memory_card_present(self) -> None:
        text = MEM.read_text(encoding="utf-8")
        self.assertIn(QUOTE_SNIP, text)

    def test_cursor_rule_always_apply(self) -> None:
        text = RULE.read_text(encoding="utf-8")
        self.assertIn("alwaysApply: true", text)
        self.assertIn("HOLD", text)

    def test_start_pin(self) -> None:
        text = START.read_text(encoding="utf-8")
        self.assertIn('id="owner-hold-quote-law"', text)
        self.assertIn("ground/HOLD_QUOTE.md", text)


if __name__ == "__main__":
    unittest.main()
