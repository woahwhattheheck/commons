#!/usr/bin/env python3
"""Hermetic: tools.json job door/manual paths."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"


class CoilToolsJsonJobDoorTest(unittest.TestCase):
    def test_paths(self) -> None:
        job = json.loads(TOOLS.read_text(encoding="utf-8"))["job"]
        self.assertEqual(job["door"], "./job.html")
        self.assertEqual(job["manual"], "./manual.html")
        self.assertEqual(job["manual_md"], "./ground/MANUAL.md")


if __name__ == "__main__":
    unittest.main()
