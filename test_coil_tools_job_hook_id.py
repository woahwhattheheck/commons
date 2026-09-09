#!/usr/bin/env python3
"""Hermetic: tools.html keeps catalog job-hook id."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.html"


class CoilToolsJobHookIdTest(unittest.TestCase):
    def test_hook(self) -> None:
        text = TOOLS.read_text(encoding="utf-8")
        self.assertIn('id="job-hook"', text)
        self.assertIn("Catalog job hook", text)
        self.assertIn("tools.json", text)
        self.assertIn("job.html", text)


if __name__ == "__main__":
    unittest.main()
