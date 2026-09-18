#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['8bit.html', '8walk.html', 'accordion.html', 'annex.html', 'archive.html', 'books.html', 'claims.html', 'glyphs.html', 'program.html', 'breath.html', 'foldbook.html', 'loop.html', 'flipbook.html', 'swarm.html', 'world.html', 'data.html']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepPointerBatch20260909bTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
