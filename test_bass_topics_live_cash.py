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
    self.assertIn('id="buy-now-live-checkout"',t)
    # Convert shelf reuses existing live buys; Live cash product-page
    # doors stay relative (type-trust-topics-convert-shelf-20260917-01).
    live_cash=t.split('id="live-cash"',1)[1].split("</section>",1)[0]
    self.assertNotIn("buy.stripe.com",live_cash)
if __name__=="__main__": unittest.main()
