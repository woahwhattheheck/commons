#!/usr/bin/env python3
"""Hermetic: llms.txt cites tools.json catalog."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LLMS = ROOT / "llms.txt"


class CoilLlmsToolsJsonTest(unittest.TestCase):
    def test_catalog(self) -> None:
        text = LLMS.read_text(encoding="utf-8")
        self.assertIn("tools.json", text)
        self.assertIn("job.html", text)


if __name__ == "__main__":
    unittest.main()
