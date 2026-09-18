#!/usr/bin/env python3
"""Hermetic: tools.json job.fields stay locked."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"
EXPECTED = ["from", "to", "id", "tool", "op"]


class CoilJobFieldsLockTest(unittest.TestCase):
    def test_job_fields(self) -> None:
        job = json.loads(TOOLS.read_text(encoding="utf-8"))["job"]
        self.assertEqual(job.get("fields"), EXPECTED)
        self.assertEqual(job.get("to"), "TOOLS")
        self.assertIn("id_pattern", job)
        self.assertIn("{claim}", job["id_pattern"])
        self.assertIn("tools", job["id_pattern"])


if __name__ == "__main__":
    unittest.main()
