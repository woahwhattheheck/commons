#!/usr/bin/env python3
"""Hermetic batch Live cash."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
HTML=["incoming-models.html","owner-net.html","dests.html","stringmail.html","cweather.html","ringdelta.html","unbuilt-items.html","paperwork-included.html"]
MD=["mirror-writeback.md","owner-context.md","play-inhabit.md","ship-loop-prompt.md","window-miss.md"]
class T(unittest.TestCase):
    def test(self) -> None:
        for name in HTML:
            text=(ROOT/name).read_text(encoding='utf-8')
            self.assertIn('id="live-cash"', text, name)
            self.assertIn('dealer-service-lead-rescue.html', text, name)
        for name in MD:
            text=(ROOT/name).read_text(encoding='utf-8')
            self.assertIn('## Live cash', text, name)
            self.assertIn('dealer-service-lead-rescue.html', text, name)
if __name__=='__main__':
    unittest.main()
