#!/usr/bin/env python3
"""Hermetic: tools.json cash.note forbids invented Stripe links."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"


class CoilToolsCashNoteTest(unittest.TestCase):
    def test_cash_note_law(self) -> None:
        cash = json.loads(TOOLS.read_text(encoding="utf-8"))["cash"]
        note = cash.get("note") or ""
        self.assertTrue(note, "cash.note missing")
        low = note.lower()
        self.assertIn("no invented stripe", low)
        self.assertIn("product", low)
        # tip-shelf / autopsy cite trail
        self.assertTrue(
            "tip-shelf" in low or "tip shelf" in low or "forge" in low,
            "cash.note should cite tip-shelf/forge trail",
        )


if __name__ == "__main__":
    unittest.main()
