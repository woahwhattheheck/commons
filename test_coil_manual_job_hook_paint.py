#!/usr/bin/env python3
"""Hermetic: manual.html paints tools.json job hook (≠ Live-cash)."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "manual.html"


class CoilManualJobHookPaintTest(unittest.TestCase):
    def test_job_hook_paint(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="job-hook"', text)
        self.assertIn("data.job", text)
        self.assertIn("Catalog job hook", text)
        self.assertIn("job.door", text)
        self.assertIn("job.button", text)
        # still paints button/share/catalog
        self.assertIn('getElementById("button")', text)
        self.assertIn('getElementById("share")', text)


if __name__ == "__main__":
    unittest.main()
