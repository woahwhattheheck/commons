#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['dests.html', 'diagnostic.html', 'distribution.html', 'distro.html', 'dj-trail.html', 'eagletrax-split-sample-preflight-lims.html', 'elevatebio-pittsburgh-replication-lims.html', 'embassy.html', 'entry.html', 'feature-requests.html', 'feature-tracker.html', 'features.html', 'federated-ci.html', 'film.html', 'first-night.html', 'fleet-work-order.html', 'free-sample.html', 'gpt-grok-ship-loop.html', 'grave-card.html', 'grounding.html']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepPointerBatch20260909iTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
