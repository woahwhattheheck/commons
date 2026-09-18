#!/usr/bin/env python3
"""Hermetic: reply→cash handoff for CommUnityCare arms only on verified YES."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HANDOFF = (
    ROOT
    / "revenue"
    / "reply_to_revenue"
    / "handoffs"
    / "communitycare-katherine-reyes.json"
)
PRODUCT = ROOT / "referral-intake-completeness.html"


class TestForgeReplyCashCommunityCare(unittest.TestCase):
    def test_standby_until_verified_yes(self) -> None:
        handoff = json.loads(HANDOFF.read_text(encoding="utf-8"))
        self.assertEqual(handoff.get("kind"), "REPLY_TO_CASH_HANDOFF")
        self.assertEqual(
            handoff.get("subject_id"), "communitycare-katherine-reyes"
        )
        self.assertIs(handoff.get("human_reply_observed"), False)
        self.assertEqual(handoff.get("arms_on"), "VERIFIED_HUMAN_YES")
        self.assertEqual(handoff.get("cash_usd"), 0)
        self.assertEqual(handoff.get("transport"), "NONE")
        self.assertTrue(handoff.get("no_second_crm"))
        on_yes = handoff.get("on_yes") or {}
        self.assertEqual(on_yes.get("product_page"), "referral-intake-completeness.html")
        self.assertEqual(on_yes.get("offer_usd"), 199)
        url = on_yes.get("payment_url") or ""
        self.assertTrue(url.startswith("https://buy.stripe.com/"))

    def test_checkout_url_matches_product_page_cta(self) -> None:
        handoff = json.loads(HANDOFF.read_text(encoding="utf-8"))
        url = handoff["on_yes"]["payment_url"]
        html = PRODUCT.read_text(encoding="utf-8")
        hrefs = re.findall(r'href="(https://buy\.stripe\.com/[^"]+)"', html)
        self.assertIn(url, hrefs)


if __name__ == "__main__":
    unittest.main()
