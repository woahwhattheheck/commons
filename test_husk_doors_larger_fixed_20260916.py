#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
DOORS = ['billings-bid-1421-partner-recon.html', 'gpt-grok-ship-loop.html', 'invoice-exception-pack.html', 'keyb.html', 'keys.html', 'landed-work.html', 'lda-receipt.html', 'lexington-mrf-diversion-gate.html', 'listing-registry.html', 'lm-gtm-index.html', 'loop.html', 'mcp-conformance.html']
class HuskLargerFixedBatchTest(unittest.TestCase):
    def test_larger_fixed_on_doors(self) -> None:
        for name in DOORS:
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("Larger fixed engagements", text, name)
            self.assertIn("diagnostic.html", text, name)
            self.assertIn("commercial.html", text, name)
            self.assertIn("$12,000", text, name)
            self.assertIn("$30,000", text, name)
if __name__ == "__main__":
    unittest.main()
