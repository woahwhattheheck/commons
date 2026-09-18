#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['ground/CURSOR.md', 'ground/CURSOR_HALT.md', 'ground/CURSOR_QUOTA_HOLD.md', 'ground/CUSTOMER_LINK_BOUNDARY.md', 'ground/DEBTS_TO_BRYCE_20260820.md', 'ground/DELTA.md', 'ground/DEST_IS_THE_MACHINE.md', 'ground/DEVICE_CANARY.md', 'ground/DEVICE_CHURN.md', 'ground/DEVICE_PATH_CANARY.md', 'ground/DEVICE_PATH_CENSUS.md', 'ground/DEVICE_QUEUE_CAP.md', 'ground/DIO_CRLF.md', 'ground/DISCORD.md', 'ground/DISTRIBUTION.md', 'ground/DURABILITY.md', 'ground/ELITIST_WAY.md', 'ground/EMBASSY.md', 'ground/EXACT_BODY_REDACT.md', 'ground/EXECUTE.md', 'ground/EXPAND.md', 'ground/FEATURES.md', 'ground/FEATURE_TRACKER.md', 'ground/FILE_MAP.md', 'ground/FILE_STRUCTURE.md']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepMdPointer20260909dTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
