#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import unittest
from pathlib import Path
PAGE=Path(__file__).resolve().parent/"revenue/billings_bid_1421/operations_package/billings-bid-1421-operations-package.md"
SLACK_OPS="49d6d56a5726d598966e8185ec84f3401faf405a9f8a0ccb9804248ad13885bc"
class T(unittest.TestCase):
  def test(self):
    b=PAGE.read_bytes()
    self.assertEqual(hashlib.sha256(b).hexdigest(), SLACK_OPS)
    t=b.decode("utf-8")
    self.assertNotIn("buy.stripe.com", t)
if __name__=="__main__": unittest.main()
