#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ["titan-hands-free-sample.html", "resources.html"]
REQUIRED = ['id="live-cash"', "./agent-rescue.html", "$29 Autopsy", "$199 dealer diagnostic"]
class LatchTitanDoorsLiveCashTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text, f"{name} missing {n}")
if __name__ == "__main__":
    unittest.main()
