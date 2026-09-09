#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['README.md', 'docs/COMMONS_ANDROID_APK.md', 'docs/GIT_BUNDLE_INSPECTOR.md', 'docs/GROKCOM_REVENUE_ORCHESTRATOR.md', 'docs/PFC_BAKE_CENSUS.md', 'docs/bugfix-deployment.md', 'docs/commons-gateway/CONTRACT.md', 'docs/commons-gateway/README.md', 'docs/commons-transport-outcomes.md', 'docs/paid-opportunities.md', 'ground/01_NONPROVISIONAL_CONVERSION_PLAN.md', 'ground/02_FOLLOWON_PROVISIONAL_NEW_MATTER_DRAFT.md', 'ground/03_EVIDENCE_ANNEX.md', 'ground/ACCORDION.md', 'ground/ACTION_DOOR.md', 'ground/AGENT_GROUNDING.md', 'ground/AGENT_RETIREMENT.md', 'ground/AGENT_TOOLKIT.md', 'ground/AGENT_TOOLKIT_AUDIT.md', 'ground/ANNEX.md', 'ground/APK.md', 'ground/AUTHORSHIP.md', 'ground/BACKUP_OPEN_REPO.md', 'ground/BATTERY_RED.md', 'ground/BAZAAR.md']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepMdPointer20260909Test(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
