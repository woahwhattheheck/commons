#!/usr/bin/env python3
"""Hermetic: host/muhl_tools_once.py exists and keeps PC --go + tools board cites."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# test runs from repo root on CI/local; support both layouts
CANDIDATES = [
    ROOT / "host" / "muhl_tools_once.py",
    ROOT / "host_muhl_tools_once.py",
]


class CoilMuhlOnceExistsTest(unittest.TestCase):
    def test_exists_and_cites(self) -> None:
        path = next((p for p in CANDIDATES if p.is_file()), None)
        self.assertIsNotNone(path, "host/muhl_tools_once.py missing")
        text = path.read_text(encoding="utf-8")
        self.assertIn("--go", text)
        self.assertIn("tools.html", text)
        self.assertIn("job.html", text)
        self.assertTrue(len(text) > 200)


if __name__ == "__main__":
    unittest.main()
