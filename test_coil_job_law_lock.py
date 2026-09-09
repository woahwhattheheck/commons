#!/usr/bin/env python3
"""Hermetic: tools.json job.law keeps one-job / oldest-open rules."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"


class CoilJobLawLockTest(unittest.TestCase):
    def test_job_law(self) -> None:
        law = (json.loads(TOOLS.read_text(encoding="utf-8"))["job"].get("law") or "").lower()
        self.assertTrue(law, "job.law missing")
        self.assertIn("one job", law)
        self.assertIn("oldest", law)
        self.assertIn("pc", law)


if __name__ == "__main__":
    unittest.main()
