#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['aquatrace-work-order-b-production-foundation.html', 'aquatrace-work-order-c-reporting-offline.html', 'aquatrace-work-order-f-release-readiness.html', 'at-grok-adapter-evidence.html', 'at-grok-cmdp-evidence.html', 'commons-apk.html']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepPointerBatch20260909fTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
