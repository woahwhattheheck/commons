#!/usr/bin/env python3
"""Hermetic: ground/REPO.md Live cash."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
class T(unittest.TestCase):
    def test_live_cash(self) -> None:
        text = (ROOT / "ground" / "REPO.md").read_text(encoding="utf-8")
        self.assertIn("## Live cash", text)
        self.assertIn("agent-rescue.html", text)
        self.assertIn("$29", text)
        self.assertIn("dealer-service-lead-rescue.html", text)
        self.assertIn("$199", text)
        self.assertNotIn("buy.stripe.com", text)
if __name__ == "__main__":
    unittest.main()
