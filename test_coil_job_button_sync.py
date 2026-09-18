#!/usr/bin/env python3
"""Hermetic: tools.json job.button matches top-level button."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"
EXPECTED = "python host/muhl_tools_once.py --go"


class CoilJobButtonSyncTest(unittest.TestCase):
    def test_job_button_matches_top(self) -> None:
        data = json.loads(TOOLS.read_text(encoding="utf-8"))
        top = data.get("button")
        job_btn = data.get("job", {}).get("button")
        self.assertEqual(top, EXPECTED)
        self.assertEqual(job_btn, EXPECTED)
        self.assertEqual(top, job_btn, "job.button drifted from tools.json button")


if __name__ == "__main__":
    unittest.main()
