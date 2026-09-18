#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['ace-qat-thermal-rheology-capacity-lims.html', 'agriseed-rush-work-allocator-lims.html', 'ait-mn-metrc-capacity-gate.html', 'aquatrace-ops-acceptance.html', 'ats-asphalt-spec-result-lims.html', 'dealer-service-lead-rescue.html', 'referral-intake-completeness.html', 'plant-downtime-handoff.html', 'reply-to-revenue.html', 'titan-hour.html', 'since-you-last-looked.html', 'subzero.html', 'index.html', 'wakeup.html']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepPointerBatch20260909eTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
