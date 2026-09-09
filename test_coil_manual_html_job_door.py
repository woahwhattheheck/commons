#!/usr/bin/env python3
"""Hermetic: manual.html cites job door + tools.json."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "manual.html"


class CoilManualHtmlJobDoorTest(unittest.TestCase):
    def test_door(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn("job.html", text)
        self.assertIn("tools.json", text)


if __name__ == "__main__":
    unittest.main()
