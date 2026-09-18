#!/usr/bin/env python3
"""Hermetic: tools.html keeps models-aligned law."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.html"


class CoilToolsHtmlModelsAlignedTest(unittest.TestCase):
    def test_aligned(self) -> None:
        text = TOOLS.read_text(encoding="utf-8")
        self.assertIn("The models are aligned", text)
        self.assertIn("The humans are the threat vector", text)


if __name__ == "__main__":
    unittest.main()
