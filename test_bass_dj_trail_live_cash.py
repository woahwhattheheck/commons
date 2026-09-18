#!/usr/bin/env python3
"""Hermetic: dj-trail.html live cash product-page doors.

CONVERT MONEY SHIP reuses two existing live buy.stripe.com Payment Links on
the first-screen convert shelf. Those URLs stay out of #live-cash. Cite
latch-dj-trail-hub-eyes-convert-shelf-20260917-01 · bass live-cash doors —
do not remint. Compose: page-wide buy.stripe.com ban becomes section-scoped.
"""
from __future__ import annotations
import unittest
from pathlib import Path
PAGE=Path(__file__).resolve().parent/"dj-trail.html"
class T(unittest.TestCase):
  def test(self):
    t=PAGE.read_text(encoding="utf-8")
    self.assertIn('id="live-cash"', t)
    self.assertIn("dealer-service-lead-rescue.html", t)
    self.assertIn('id="buy-now-live-checkout"', t)
    live_cash = t.split('id="live-cash"', 1)[1].split("</section>", 1)[0]
    self.assertNotIn("buy.stripe.com", live_cash)
    self.assertNotIn("donate.stripe.com", t)
if __name__=="__main__": unittest.main()
