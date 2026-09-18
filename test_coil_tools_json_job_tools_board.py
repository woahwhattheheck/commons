#!/usr/bin/env python3
"""Hermetic: tools.json job tools-board pointer."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"


class CoilToolsJsonJobToolsBoardTest(unittest.TestCase):
    def test_job_tools_board(self) -> None:
        job = json.loads(TOOLS.read_text(encoding="utf-8"))["job"]
        self.assertEqual(job["tools_board"], "./tools.html")
        self.assertTrue((ROOT / job["tools_board"]).is_file())


if __name__ == "__main__":
    unittest.main()
