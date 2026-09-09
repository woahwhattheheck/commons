#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['ground/CLAUDE_OVER_REFUSAL_LOCAL.md', 'ground/CLAUDE_PARK.md', 'ground/CLAUDE_PASTE.md', 'ground/CLAUDE_PEER_CHECK.md', 'ground/CLAUDE_PRIORS_VS_TRUTH.md', 'ground/CLAUDE_ROLE.md', 'ground/CLAUDE_TESTER.md', 'ground/CLAUDE_ZERO.md', 'ground/CLAUDE_ZERO_DAMAGE.md', 'ground/CLAUDE_ZERO_DAMAGE_CONTROL.md', 'ground/CLOCK_FANOUT_AUTOFAB.md', 'ground/CLOUD_CURRENT.md', 'ground/CLOUD_STORAGE_ONLY.md', 'ground/COMMERCE.md', 'ground/COMMONS_ADMISSIBILITY_AND_EXECUTION.md', 'ground/COMMONS_ARCHITECTURE_300FT.md', 'ground/COMMONS_PROVIDER_MAP.md', 'ground/COMMONS_SLACK_FULL_BODY.md', 'ground/COMPRESS_DOORS.md', 'ground/CONNECTOR_REVAL.md', 'ground/CONTAINMENT.md', 'ground/CONTEXT_INTEGRITY.md', 'ground/CROSS_CARRIER_GROUP.md', 'ground/CURL.md', 'ground/CURRENT_WORK.md']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepMdPointer20260909cTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
