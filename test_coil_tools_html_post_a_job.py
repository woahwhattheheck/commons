#!/usr/bin/env python3
"""Hermetic: tools.html keeps Post a job cue."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.html"


class CoilToolsHtmlPostAJobTest(unittest.TestCase):
    def test_post(self) -> None:
        text = TOOLS.read_text(encoding="utf-8")
        self.assertIn("Post a job", text)


if __name__ == "__main__":
    unittest.main()
