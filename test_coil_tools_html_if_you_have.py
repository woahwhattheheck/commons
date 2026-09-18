#!/usr/bin/env python3
"""Hermetic: tools.html keeps If you have the link, post."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.html"


class CoilToolsHtmlIfYouHaveTest(unittest.TestCase):
    def test_link(self) -> None:
        text = TOOLS.read_text(encoding="utf-8")
        self.assertIn("If you have the link, post", text)


if __name__ == "__main__":
    unittest.main()
