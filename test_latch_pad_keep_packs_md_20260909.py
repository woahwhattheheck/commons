#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['packs/README.md', 'packs/_template/README.md', 'packs/_template/assets.md', 'packs/_template/checkout.md', 'packs/_template/creative_brief.md', 'packs/_template/day.md', 'packs/_template/instructions.md', 'packs/_template/keep-vs-sell.md', 'packs/_template/offer.md', 'packs/_template/paperwork.md', 'packs/_template/rating.md', 'packs/_template/running-cost.md', 'packs/_template/terms.md', 'packs/_template/waitlist-slot.md', 'packs/_template/week1.md', 'packs/curbline-weekend-yard-help-20260902-01/README.md', 'packs/curbline-weekend-yard-help-20260902-01/assets/brand.md', 'packs/curbline-weekend-yard-help-20260902-01/assets/card-copy.md', 'packs/curbline-weekend-yard-help-20260902-01/assets/days-8-30.md', 'packs/curbline-weekend-yard-help-20260902-01/assets/invoice-text.md', 'packs/curbline-weekend-yard-help-20260902-01/assets/job-checklist.md', 'packs/curbline-weekend-yard-help-20260902-01/assets/paperwork-checklist.md', 'packs/curbline-weekend-yard-help-20260902-01/assets/phone-script.md', 'packs/curbline-weekend-yard-help-20260902-01/assets/price-sheet.md', 'packs/curbline-weekend-yard-help-20260902-01/assets/route-log.md', 'packs/curbline-weekend-yard-help-20260902-01/assets.md', 'packs/curbline-weekend-yard-help-20260902-01/checkout.md', 'packs/curbline-weekend-yard-help-20260902-01/creative_brief.md', 'packs/curbline-weekend-yard-help-20260902-01/day.md', 'packs/curbline-weekend-yard-help-20260902-01/gems.md', 'packs/curbline-weekend-yard-help-20260902-01/instructions.md', 'packs/curbline-weekend-yard-help-20260902-01/keep-vs-sell.md', 'packs/curbline-weekend-yard-help-20260902-01/offer.md', 'packs/curbline-weekend-yard-help-20260902-01/paperwork.md', 'packs/curbline-weekend-yard-help-20260902-01/rating.md', 'packs/curbline-weekend-yard-help-20260902-01/running-cost.md', 'packs/curbline-weekend-yard-help-20260902-01/terms.md', 'packs/curbline-weekend-yard-help-20260902-01/week1.md', 'packs/desk-website-service-20260902-01/README.md', 'packs/desk-website-service-20260902-01/assets.md']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepPacksMd20260909Test(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
