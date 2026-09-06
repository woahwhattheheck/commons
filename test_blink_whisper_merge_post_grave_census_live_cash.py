#!/usr/bin/env python3
"""Hermetic batch Live cash."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
HTML = ["whisper.html","merge-on-pr.html","post-http.html","grave-card.html","open-model-release-receipt.html"]
MD = ["leftover-census.md","occupancy.md","health-canary.md","harness-ping-get.md"]
class T(unittest.TestCase):
    def test_html(self) -> None:
        for name in HTML:
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn('id="live-cash"', text, name)
            self.assertIn("agent-rescue.html", text, name)
            self.assertIn("$29", text, name)
            self.assertIn("dealer-service-lead-rescue.html", text, name)
    def test_md(self) -> None:
        for name in MD:
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("## Live cash", text, name)
            self.assertIn("agent-rescue.html", text, name)
            self.assertIn("$29", text, name)
            self.assertIn("dealer-service-lead-rescue.html", text, name)
if __name__ == "__main__":
    unittest.main()
