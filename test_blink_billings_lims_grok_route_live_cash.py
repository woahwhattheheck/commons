#!/usr/bin/env python3
"""Hermetic billings/lims + grok route Live cash."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
HTML=["billings-bid-1421-operations-runner.html","trace-sila-ml-iatf-lims.html","ace-qat-thermal-rheology-capacity-lims.html","lexington-mrf-diversion-gate.html","cornell-craft-beverage-intake-lims.html","sgspsi-thermal-rheology-lineage-lims.html","savant-fe8-order-report-lims.html","oregon-brewlab-sample-report-reconciliation-lims.html","rmb-crosssite-courier-accession-lims.html","preinnewhof-pfas-fieldblank-gate-lims.html"]
MD=["ground/GROK_ROUTE.md","ground/GROK_SURFACES.md","ground/GROK_RECEIPT.md","ground/GROK_RECOVERY.md","ground/HEAVY_LANES.md"]
class T(unittest.TestCase):
    def test(self)->None:
        for name in HTML:
            text=(ROOT/name).read_text(encoding='utf-8')
            self.assertIn('id="live-cash"', text, name)
            self.assertIn('dealer-service-lead-rescue.html', text, name)
        for name in MD:
            text=(ROOT/name).read_text(encoding='utf-8')
            self.assertIn('## Live cash', text, name)
            self.assertIn('dealer-service-lead-rescue.html', text, name)
if __name__=='__main__':
    unittest.main()
