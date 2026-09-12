#!/usr/bin/env python3
"""Hermetic: tools.html keeps Do not smash commons.mno law."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.html"


class CoilToolsHtmlDoNotSmashTest(unittest.TestCase):
    def test_smash(self) -> None:
        text = TOOLS.read_text(encoding="utf-8")
        self.assertIn("Do not smash commons.mno", text)
        self.assertIn("Do not fire 337", text)


if __name__ == "__main__":
    unittest.main()
