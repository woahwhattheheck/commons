#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['ci/README.md', 'ci/federated/README.md', 'ci/moving_main/README.md', 'infra/README.md', 'infra/oracle_always_free/README.md', 'infra/teams/README.md', 'infra/discord/README.md']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class T(unittest.TestCase):
    def test_all(self):
        for name in PAGES:
            with self.subTest(page=name):
                text=(ROOT/name).read_text(encoding='utf-8')
                for n in REQUIRED: self.assertIn(n, text)
if __name__ == '__main__':
    unittest.main()
