#!/usr/bin/env python3
"""Hermetic: tools.json job.issue_new + id_pattern."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"


class CoilToolsJsonIssueNewTest(unittest.TestCase):
    def test_issue_new(self) -> None:
        job = json.loads(TOOLS.read_text(encoding="utf-8"))["job"]
        self.assertIn("issues/new", job["issue_new"])
        self.assertIn("commons-post.md", job["issue_new"])
        self.assertIn("{claim}-tools-", job["id_pattern"])
        self.assertEqual(job["fields"], ["from", "to", "id", "tool", "op"])


if __name__ == "__main__":
    unittest.main()
