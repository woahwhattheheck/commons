#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
PAGE=Path(__file__).resolve().parent/"delta.html"
class T(unittest.TestCase):
  def test(self):
    t=PAGE.read_text(encoding="utf-8")
    self.assertIn('id="live-cash"',t)
    self.assertIn("dealer-service-lead-rescue.html",t)
    # Convert shelf reuses existing live buys; Live cash product-page
    # doors stay relative (wire-live-delta-convert-shelf-20260917-01).
    live_cash = t.split('id="live-cash"', 1)[1].split("</section>", 1)[0]
    self.assertNotIn("buy.stripe.com", live_cash)
if __name__=="__main__": unittest.main()
