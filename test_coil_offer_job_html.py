#!/usr/bin/env python3
"""Hermetic: offer.html law cites job.html (≠ tools-board note remint)."""

from __future__ import annotations

import unittest
from pathlib import Path

PAGE = Path(__file__).resolve().parent / "offer.html"


class CoilOfferJobHtmlTest(unittest.TestCase):
    def test_job_html_in_law(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('./job.html', text)
        self.assertIn('./tools.html', text)
        self.assertIn("muhl-hook", text)
        # not a tools-board note clone
        self.assertNotIn('id="tools-board"', text)


if __name__ == "__main__":
    unittest.main()
