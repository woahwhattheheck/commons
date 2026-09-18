#!/usr/bin/env python3
"""Creative brief leftover. Does not steal GOAT template files or peer packs."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import pack_creative_brief as brief  # noqa: E402


EARNINGS = """# Creative brief
## Buyer
Laptop Lena
## Hooks
make $200 this weekend
## Runtime
15 seconds
## CTA
$200
## Anchor
x
## Channel order
X
## Launch metros
Phoenix
## Never say
earnings never
## UTM
?utm_source={channel}&utm_medium=paid&utm_campaign=x&utm_content=door
?utm_source={channel}&utm_medium=paid&utm_campaign=x&utm_content=thanks
"""

DONE_FOR_YOU = EARNINGS.replace("make $200 this weekend", "done for you build")

MISSING = """# Creative brief
## Buyer
Laptop Lena
## Hooks
broken site
"""


class CreativeBriefTest(unittest.TestCase):
    def test_does_not_claim_peer_paths(self) -> None:
        self.assertIn("packs/_template/checkout.md", brief.DO_NOT_OVERWRITE)
        self.assertIn("packs/sidewalk-signal-web-desk-20260902-01", brief.DO_NOT_OVERWRITE)
        self.assertIn("packs/lotribbon-greetings-20260902-01", brief.DO_NOT_OVERWRITE)
        self.assertIn("packs/desk-website-service-20260902-01/door.html", brief.DO_NOT_OVERWRITE)
        self.assertIn("host/business_pack_desk_instance.py", brief.DO_NOT_OVERWRITE)
        self.assertIn("revenue/business_packs_marketing/BUYER_TIERS.md", brief.DO_NOT_OVERWRITE)
        self.assertIn("packs/waitlist.html", brief.DO_NOT_OVERWRITE)
        self.assertIn("packs/thanks.html", brief.DO_NOT_OVERWRITE)

    def test_template_slots_stay_owner_unset(self) -> None:
        if not brief.TEMPLATE.is_file():
            self.skipTest("template not in this tree")
        result = brief.classify_path(brief.TEMPLATE, kind="template")
        self.assertEqual(result["verdict"], "CREATIVE_BRIEF_TEMPLATE_OK")
        self.assertTrue(result["owner_unset_present"])
        self.assertFalse(result["earnings_claim"])
        self.assertEqual(result["sends"], 0)
        self.assertEqual(result["checkout"], "NOT_MINTED")

    def test_harborline_instance_is_filled(self) -> None:
        if not brief.HARBORLINE.is_file():
            self.skipTest("Harborline brief not in this tree")
        result = brief.classify_path(brief.HARBORLINE, kind="instance")
        text = brief.HARBORLINE.read_text(encoding="utf-8")
        self.assertEqual(result["verdict"], "CREATIVE_BRIEF_INSTANCE_OK")
        self.assertIn("Harborline Local Sites", text)
        self.assertIn("Laptop Lena", text)
        self.assertIn("OWNER_UNSET", text)
        self.assertIn("utm_content=thanks", text.lower())
        scored = brief.strip_section(text, "Never say")
        self.assertNotIn("done for you", scored.lower())
        self.assertFalse(result["earnings_claim"])
        self.assertFalse(result["agents_spend_ads"])

    def test_earnings_copy_fails(self) -> None:
        result = brief.classify(EARNINGS, kind="instance")
        self.assertEqual(result["verdict"], "CREATIVE_BRIEF_EARNINGS")
        self.assertTrue(result["earnings_claim"])

    def test_done_for_you_fails(self) -> None:
        result = brief.classify(DONE_FOR_YOU, kind="instance")
        self.assertEqual(result["verdict"], "CREATIVE_BRIEF_EARNINGS")
        self.assertTrue(result["forbidden_phrase"])

    def test_missing_headings_incomplete(self) -> None:
        result = brief.classify(MISSING, kind="instance")
        self.assertEqual(result["verdict"], "CREATIVE_BRIEF_INCOMPLETE")
        self.assertIn("Runtime", result["missing_headings"])
        self.assertIn("headings", result["problems"])

    def test_tree_ok_when_both_present(self) -> None:
        if not brief.TEMPLATE.is_file() or not brief.HARBORLINE.is_file():
            self.skipTest("brief files not in this tree")
        result = brief.classify_tree()
        self.assertEqual(result["verdict"], "CREATIVE_BRIEF_OK")
        self.assertTrue(result["did_not_fill_sidewalk"])
        self.assertTrue(result["did_not_overwrite_harborline_door"])
        dumped = json.dumps(result)
        self.assertNotIn("337 NO", dumped)
        self.assertEqual(result["checkout"], "NOT_MINTED")


if __name__ == "__main__":
    unittest.main()
