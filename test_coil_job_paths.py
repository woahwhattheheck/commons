#!/usr/bin/env python3
"""Hermetic: tools.json job door/manual/board paths resolve to files."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"
KEYS = ("door", "manual", "manual_md", "tools_board")


class CoilJobPathsTest(unittest.TestCase):
    def test_job_paths_exist(self) -> None:
        job = json.loads(TOOLS.read_text(encoding="utf-8"))["job"]
        for key in KEYS:
            rel = job.get(key) or ""
            self.assertTrue(rel.startswith("./"), f"{key}={rel}")
            self.assertTrue((ROOT / rel[2:]).is_file(), f"missing {key} -> {rel}")


if __name__ == "__main__":
    unittest.main()
