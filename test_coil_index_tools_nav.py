#!/usr/bin/env python3
"""Hermetic: index.html nav cites tools + job doors."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"


class CoilIndexToolsNavTest(unittest.TestCase):
    def test_nav(self) -> None:
        text = INDEX.read_text(encoding="utf-8")
        self.assertIn("tools.html", text)
        self.assertIn("job.html", text)


if __name__ == "__main__":
    unittest.main()
