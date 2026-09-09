#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['ground/HIS_11.md', 'ground/HOARD.md', 'ground/HOLD_QUOTE.md', 'ground/HOST_ZERO.md', 'ground/HUB.md', 'ground/HUB_TICK.md', 'ground/HUMAN_OUTCOMES.md', 'ground/IMPACT_LEDGER.md', 'ground/INCOMING_MODELS.md', 'ground/INTERCONNECT.md', 'ground/INVENTION_BURST_INDEX.md', 'ground/IP_FILING_INDEX.md', 'ground/JOJO_ASSIGN.md', 'ground/LAB.md', 'ground/LAND.md', 'ground/LDA_ANDROID_CI.md', 'ground/LDA_RECEIPT.md', 'ground/LISTING_REGISTRY.md', 'ground/MANUAL.md', 'ground/MEASURE_ABUSE.md', 'ground/MEMORY_SHIP.md', 'ground/MEMORY_VISIBLE.md', 'ground/MIRROR_MESH_0.md', 'ground/MNO_DATASHEETS_20260819.md', 'ground/MODEL_LANGUAGE.md']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepMdPointer20260909fTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
