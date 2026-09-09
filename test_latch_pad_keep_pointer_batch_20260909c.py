#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['visual.html', 'look.html', 'shots.html', 'face.html', 'mirrors.html', 'autogtm.html', 'claudes.html', 'commerce.html', 'avatars.html', 'nojs.html', 'reply.html', 'salon.html', 'lab.html', 'unlisted.html', 'vent.html', 'future.html', 'requests.html', 'failed.html', 'titan-hands-free-sample.html']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepPointerBatch20260909cTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
