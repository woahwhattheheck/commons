#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['ground/MOVING_MAIN_MIRROR.md', 'ground/MUHC.md', 'ground/MUHC_CORPUS.md', 'ground/MUHL_FILM_ORGAN.md', 'ground/MUHL_PNG.md', 'ground/MUHL_RECEIPT_LANE.md', 'ground/MUHL_SELF_TRAIN_ADDRESS_CONTRACT.md', 'ground/MUHL_TRAIN_BRIDGE.md', 'ground/NAMED_BUILDER.md', 'ground/NEEDS_BRYCE.md', 'ground/NO_MOCK_ONLY.md', 'ground/OBSERVATORY.md', 'ground/OBS_ADDITIVE.md', 'ground/OPEN-DOOR.md', 'ground/OPEN_DOOR.md', 'ground/OPEN_WORK.md', 'ground/OPPORTUNITY_REGISTRY.md', 'ground/OWNER_CONTEXT.md', 'ground/OWNER_MACHINE_BUILD_SWEEP.md', 'ground/OWNER_NOW.md', 'ground/P4_CLOSED.md', 'ground/PAGES_DEPLOY.md', 'ground/PAGES_DEPLOY_RECEIPT.md', 'ground/PAGES_KEEP_PATHS.md', 'ground/PAY.md']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepMdPointer20260909gTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
