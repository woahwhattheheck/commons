#!/usr/bin/env python3
"""Hermetic ground hub/swarm/play + mirror/humans Live cash."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
HTML=["mirror.html","task-forge.html","tabletop.html","website-people-email-book.html","muhlnickel-free-sample.html","humans.html","reply-to-revenue.html"]
MD=["ground/HUB.md","ground/SWARM.md","ground/PLAY.md","ground/FLEET.md","ground/LAB.md","ground/TOPICS.md","ground/FEATURES.md","ground/OPEN_DOOR.md","ground/NEEDS_BRYCE.md","ground/GROK_HARNESS.md"]
class T(unittest.TestCase):
    def test(self)->None:
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
