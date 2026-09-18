#!/usr/bin/env python3
"""Hermetic: index.html keeps file a job door."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"


class CoilIndexFileAJobTest(unittest.TestCase):
    def test_door(self) -> None:
        text = INDEX.read_text(encoding="utf-8")
        self.assertIn("file a job", text.lower())
        self.assertIn("job.html", text)


if __name__ == "__main__":
    unittest.main()
