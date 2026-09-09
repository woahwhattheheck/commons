#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
PAGE=Path(__file__).resolve().parent/".agents/skills/grok-web-commons/SKILL.md"
class T(unittest.TestCase):
  def test(self):
    t=PAGE.read_text(encoding="utf-8")
    self.assertIn("](../../../agent-rescue.html)", t)
    self.assertNotIn("](../../agent-rescue.html)", t)
if __name__=="__main__": unittest.main()
