#!/usr/bin/env python3
"""Hermetic: job.html form keeps from/tool/op/title + body to: TOOLS."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JOB = ROOT / "job.html"


class CoilJobHtmlFieldsTest(unittest.TestCase):
    def test_fields(self) -> None:
        text = JOB.read_text(encoding="utf-8")
        for f in ("from", "tool", "op", "title", "body"):
            self.assertIn(f'name="{f}"', text)
        self.assertIn("to: TOOLS", text)
        self.assertIn("tools.json", text)


if __name__ == "__main__":
    unittest.main()
