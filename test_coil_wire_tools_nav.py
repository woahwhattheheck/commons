#!/usr/bin/env python3
"""Hermetic: wire.html cites tools door."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WIRE = ROOT / "wire.html"


class CoilWireToolsNavTest(unittest.TestCase):
    def test_nav(self) -> None:
        text = WIRE.read_text(encoding="utf-8")
        self.assertIn("tools.html", text)


if __name__ == "__main__":
    unittest.main()
