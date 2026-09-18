#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
PAGE=Path(__file__).resolve().parent/"artifacts/muhlnickel-tick-topology-20260827/README.md"
class T(unittest.TestCase):
  def test(self):
    t=PAGE.read_text(encoding="utf-8")
    self.assertIn("## Live cash", t)
    self.assertIn("../../dealer-service-lead-rescue.html", t)
    self.assertNotIn("buy.stripe.com", t)
if __name__=="__main__": unittest.main()
