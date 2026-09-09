#!/usr/bin/env python3
"""Hermetic: llms.txt keeps Dest FROM FILE law."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LLMS = ROOT / "llms.txt"


class CoilLlmsDestFromFileTest(unittest.TestCase):
    def test_law(self) -> None:
        text = LLMS.read_text(encoding="utf-8")
        self.assertIn("Dest FROM FILE", text)


if __name__ == "__main__":
    unittest.main()
