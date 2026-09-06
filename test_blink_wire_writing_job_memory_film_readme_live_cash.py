#!/usr/bin/env python3
"""Hermetic: wire/writing/job/memory/film/chunk/feature-requests/net159 + README tip-shelf."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
HTML = ["wire.html","writing.html","job.html","memory.html","film.html","commons-slack-chunk.html","feature-requests.html","net159.html"]
class T(unittest.TestCase):
    def test_html(self) -> None:
        for name in HTML:
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn('id="live-cash"', text, name)
            self.assertIn("agent-rescue.html", text, name)
            self.assertIn("dealer-service-lead-rescue.html", text, name)
    def test_readme(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("dealer-service-lead-rescue.html", text)
        self.assertIn("referral-intake-completeness.html", text)
        self.assertIn("repair-booking-preflight.html", text)
        self.assertIn("plant-downtime-handoff.html", text)
        self.assertIn("$29", text)
if __name__ == "__main__":
    unittest.main()
