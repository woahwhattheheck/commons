#!/usr/bin/env python3
"""Hermetic: ground/MANUAL.md cites tools.json catalog."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "ground" / "MANUAL.md"


class CoilGroundManualToolsJsonTest(unittest.TestCase):
    def test_catalog(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn("tools.json", text)
        self.assertIn("job.html", text)


if __name__ == "__main__":
    unittest.main()
