#!/usr/bin/env python3
"""Hermetic: llms.txt cites PC command host/muhl_tools_once.py --go."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LLMS = ROOT / "llms.txt"


class CoilLlmsMuhlOnceTest(unittest.TestCase):
    def test_muhl(self) -> None:
        text = LLMS.read_text(encoding="utf-8")
        self.assertIn("python host/muhl_tools_once.py --go", text)
        self.assertIn("host/muhl_tools_once.py", text)


if __name__ == "__main__":
    unittest.main()
