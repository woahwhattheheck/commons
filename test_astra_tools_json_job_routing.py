#!/usr/bin/env python3
"""Hermetic: tools.json job routing contract."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"


class AstraToolsJsonJobRoutingTest(unittest.TestCase):
    def test_job_routes_to_tools_board(self) -> None:
        job = json.loads(TOOLS.read_text(encoding="utf-8"))["job"]
        self.assertEqual(job["to"], "TOOLS")
        self.assertEqual(job["tools_board"], "./tools.html")
        self.assertTrue((ROOT / job["tools_board"][2:]).is_file())


if __name__ == "__main__":
    unittest.main()
