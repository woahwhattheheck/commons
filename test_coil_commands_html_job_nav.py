#!/usr/bin/env python3
"""Hermetic: commands.html nav keeps job.html next to tools.html."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "commands.html"


class CoilCommandsHtmlJobNavTest(unittest.TestCase):
    def test_job_nav(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn("job.html", text)
        self.assertIn("tools.html", text)
        # job link appears near tools link in nav
        t_idx = text.index("tools.html")
        j_idx = text.index("job.html")
        self.assertLess(abs(t_idx - j_idx), 400)


if __name__ == "__main__":
    unittest.main()
