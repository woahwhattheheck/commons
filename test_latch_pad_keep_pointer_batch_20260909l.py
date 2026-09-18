#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['orchestration.html', 'oregon-brewlab-sample-report-reconciliation-lims.html', 'organabio-multisite-donor-coa.html', 'owner-net.html', 'owner-now-revenue.html', 'owner.html', 'pace-lebanon-microbial-volume-evidence-lims.html', 'pack-is-ready-to-run.html', 'pack-quality-tier.html', 'paid-opportunities.html', 'panel.html', 'paperwork-included.html', 'paragon-biodiesel-sample-coa-lims.html', 'patent-products.html', 'pay.html', 'payment-capability.html', 'pcl-scope-sla-routing-lims.html', 'peers.html', 'permit-intake-receipt.html', 'pixel-portfolio.html']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepPointerBatch20260909lTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
