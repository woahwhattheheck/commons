#!/usr/bin/env python3
"""Hermetic: tools.json job.button is the PC command."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"


class CoilToolsJsonButtonTest(unittest.TestCase):
    def test_button(self) -> None:
        job = json.loads(TOOLS.read_text(encoding="utf-8"))["job"]
        self.assertEqual(job["button"], "python host/muhl_tools_once.py --go")
        self.assertEqual(job["to"], "TOOLS")


if __name__ == "__main__":
    unittest.main()
