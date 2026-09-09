#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['ground/PAYMENT_CAPABILITY.md', 'ground/PAYMENT_READY.md', 'ground/PC_SHARE.md', 'ground/PEER_KIT.md', 'ground/PEER_PACKET_20260819.md', 'ground/PEER_WAKE_BUS.md', 'ground/PFC_BAKE_CENSUS.md', 'ground/PFC_COMPUTER.md', 'ground/PFC_GROUNDING.md', 'ground/PFC_PROOF_REPORT.md', 'ground/PFC_X_DEFINED.md', 'ground/PICK.md', 'ground/PIXEL_HEARTBEAT.md', 'ground/PLAY.md', 'ground/PORTFOLIO_OVERDRIVE.md', 'ground/POST_CURL.md', 'ground/POWER_CORD_DEMO.md', 'ground/PREDICATE_JAIL.md', 'ground/PROFITABILITY_BUILD_MAP.md', 'ground/PROOF_TO_PROPOSAL.md', 'ground/PRTSCN.md', 'ground/README.md', 'ground/README_LIVE.md', 'ground/READ_IS_VOLTAGE.md', 'ground/REMEASURE.md']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepMdPointer20260909hTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
