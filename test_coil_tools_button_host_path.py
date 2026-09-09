#!/usr/bin/env python3
"""Hermetic: tools.html cites PC button host/muhl_tools_once.py --go."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.html"


class CoilToolsButtonHostPathTest(unittest.TestCase):
    def test_host_path(self) -> None:
        text = TOOLS.read_text(encoding="utf-8")
        self.assertIn("host/muhl_tools_once.py", text)
        self.assertIn("--go", text)
        self.assertIn("python host/muhl_tools_once.py --go", text)


if __name__ == "__main__":
    unittest.main()
