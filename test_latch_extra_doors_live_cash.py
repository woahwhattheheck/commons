#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['attested-inference.html', 'ccc-snapshot-toolchain.html']
REQUIRED = ['id="live-cash"', "./agent-rescue.html", "$29 Autopsy", "$199 dealer diagnostic"]
class LatchExtraDoorsLiveCashTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED: self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
