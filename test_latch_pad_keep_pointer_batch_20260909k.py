#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['live.html', 'lm-gtm-index.html', 'luvak-ssa-lab-analytics-cutover-lims.html', 'made-scientific-princeton-rapid-qc-lims.html', 'manual.html', 'memory.html', 'merge-on-pr.html', 'mirror-capsule.html', 'mirror.html', 'mod.html', 'muhl-train.html', 'muhlnickel-free-sample.html', 'names.html', 'needs-bryce.html', 'net159.html', 'observatory.html', 'offer.html', 'open-door.html', 'open-model-release-receipt.html', 'opportunity.html']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepPointerBatch20260909kTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
