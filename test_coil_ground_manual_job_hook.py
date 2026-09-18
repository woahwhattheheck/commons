#!/usr/bin/env python3
"""Hermetic: ground/MANUAL.md keeps Catalog job hook + File a job."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = [
    ROOT / "ground" / "MANUAL.md",
    ROOT / "MANUAL.md",
]


class CoilGroundManualJobHookTest(unittest.TestCase):
    def test_job_hook(self) -> None:
        path = next((p for p in CANDIDATES if p.is_file()), None)
        self.assertIsNotNone(path)
        text = path.read_text(encoding="utf-8")
        self.assertIn("## File a job", text)
        self.assertIn("Catalog job hook", text)
        self.assertIn("tools.json", text)
        self.assertIn("job.html", text)
        self.assertIn("muhl_tools_once.py --go", text)
        self.assertIn("to: TOOLS", text)


if __name__ == "__main__":
    unittest.main()
