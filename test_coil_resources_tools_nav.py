#!/usr/bin/env python3
"""Hermetic: resources.html cites tools + job doors."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RES = ROOT / "resources.html"


class CoilResourcesToolsNavTest(unittest.TestCase):
    def test_nav(self) -> None:
        text = RES.read_text(encoding="utf-8")
        self.assertIn("tools.html", text)
        self.assertIn("job.html", text)


if __name__ == "__main__":
    unittest.main()
