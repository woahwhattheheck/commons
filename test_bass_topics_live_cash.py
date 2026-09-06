#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
PAGE=Path(__file__).resolve().parent/"topics.html"
class T(unittest.TestCase):
  def test(self):
    t=PAGE.read_text(encoding="utf-8")
    self.assertIn('id="live-cash"',t)
    self.assertIn("dealer-service-lead-rescue.html",t)
    self.assertNotIn("buy.stripe.com",t)
if __name__=="__main__": unittest.main()
