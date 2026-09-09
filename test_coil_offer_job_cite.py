#!/usr/bin/env python3
"""Hermetic: offer.html cites job.html for TOOLS jobs."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OFFER = ROOT / "offer.html"


class CoilOfferJobCiteTest(unittest.TestCase):
    def test_job_cite(self) -> None:
        text = OFFER.read_text(encoding="utf-8")
        self.assertIn("job.html", text)
        self.assertTrue("TOOLS" in text or "tools" in text.lower())
        self.assertGreater(len(text), 200)


if __name__ == "__main__":
    unittest.main()
