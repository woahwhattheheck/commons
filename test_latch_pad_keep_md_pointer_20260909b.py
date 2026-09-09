#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['ground/BOOKS.md', 'ground/BRANCH_REVIEW.md', 'ground/BRANCH_TRUTH_DELTA.md', 'ground/BREATH.md', 'ground/BRYCE_BUILD_ASKS.md', 'ground/BRYCE_EXECUTION_PROFILE.md', 'ground/BUILD_SWEEP_ACT.md', 'ground/BUSINESS_PACKS.md', 'ground/BUSINESS_PACK_KEEP_SELL.md', 'ground/BUSINESS_PACK_OPERATOR.md', 'ground/BUSINESS_PACK_PAPERWORK.md', 'ground/BUSINESS_PACK_PAPERWORK_FILLED.md', 'ground/BUSINESS_PACK_PAPERWORK_INCLUDED.md', 'ground/BUSINESS_PACK_PAPERWORK_SLOT.md', 'ground/BUSINESS_PACK_RATING.md', 'ground/BUSINESS_PACK_RUNNING_COST.md', 'ground/CARRIER_PICKUP.md', 'ground/CASH_NOW.md', 'ground/CCC_VAULT_HARVEST.md', 'ground/CHECKOUT_CAPABILITY.md', 'ground/CIRCUIT_PFC.md', 'ground/CLANS.md', 'ground/CLASS_17.md', 'ground/CLAUDE_COMPUTE.md', 'ground/CLAUDE_INTERMEDIATE.md']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepMdPointer20260909bTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
