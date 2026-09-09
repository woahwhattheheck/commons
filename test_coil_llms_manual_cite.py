#!/usr/bin/env python3
"""Hermetic: llms.txt cites manual.html."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LLMS = ROOT / "llms.txt"


class CoilLlmsManualCiteTest(unittest.TestCase):
    def test_manual(self) -> None:
        text = LLMS.read_text(encoding="utf-8")
        self.assertIn("manual.html", text)
        self.assertIn("tools.html", text)


if __name__ == "__main__":
    unittest.main()
