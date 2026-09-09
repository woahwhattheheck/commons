#!/usr/bin/env python3
"""Hermetic: ground/PICK.md cites tools.html door."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PICK = ROOT / "ground" / "PICK.md"


class CoilGroundPickToolsTest(unittest.TestCase):
    def test_tools(self) -> None:
        text = PICK.read_text(encoding="utf-8")
        self.assertIn("tools.html", text)
        self.assertIn("boards.html", text)


if __name__ == "__main__":
    unittest.main()
