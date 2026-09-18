#!/usr/bin/env python3
"""Hermetic: wakeup.html cites tools.json catalog."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WAKE = ROOT / "wakeup.html"


class CoilWakeupToolsJsonTest(unittest.TestCase):
    def test_catalog(self) -> None:
        text = WAKE.read_text(encoding="utf-8")
        self.assertIn("tools.json", text)
        self.assertIn("job.html", text)


if __name__ == "__main__":
    unittest.main()
