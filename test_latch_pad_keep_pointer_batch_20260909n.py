#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['sanair-asbestos-coc-router-lims.html', 'savant-fe8-order-report-lims.html', 'sc-labs-multistate-coa-rule-version-gate.html', 'scope-to-delivery.html', 'sgspsi-thermal-rheology-lineage-lims.html', 'sharp-rtu-vial-isolator-lineage-lims.html', 'skills.html', 'slack-tags.html', 'slo-cls-cutover-evidence-lims.html', 'start.html', 'stealable-lanes.html', 'stringmail.html', 'stripe-payment-links-20260826.html', 'subzero-proof.html', 'subzero-quote.html', 'subzero-receipt.html', 'super-mcp.html', 'swarm-dc.html', 'swarm-mail.html', 'tabletop.html']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepPointerBatch20260909nTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
