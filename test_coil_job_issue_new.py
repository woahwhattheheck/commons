#!/usr/bin/env python3
"""Hermetic: tools.json job.issue_new points at commons board issue template."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"


class CoilJobIssueNewTest(unittest.TestCase):
    def test_issue_new_url(self) -> None:
        url = json.loads(TOOLS.read_text(encoding="utf-8"))["job"]["issue_new"]
        self.assertTrue(url.startswith("https://github.com/woahwhattheheck/commons/issues/new"), url)
        self.assertIn("template=commons-post.md", url)
        self.assertIn("labels=board", url)


if __name__ == "__main__":
    unittest.main()
