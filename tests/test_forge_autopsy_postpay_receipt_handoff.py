#!/usr/bin/env python3
"""Hermetic: Autopsy $29 page carries post-pay receipt→handoff copy.

CLAIM forge-autopsy-postpay-receipt-handoff-20260906-01
Parity with #8981 diag postpay. Does not remint Autopsy plink.
Hands off #8802.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "agent-rescue.html"
PLINK = "https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g"
RECEIPT = ROOT / "p" / "forge-autopsy-postpay-receipt-handoff-20260906-01.md"


class TestForgeAutopsyPostpayReceiptHandoff(unittest.TestCase):
    def test_autopsy_has_postpay_handoff(self) -> None:
        raw = PAGE.read_text(encoding="utf-8")
        self.assertIn('data-postpay-handoff="1"', raw)
        self.assertIn("After purchase", raw)
        self.assertIn("Stripe receipt", raw)
        self.assertIn("mailto:tokenjunkielabs@gmail.com", raw)
        self.assertIn(PLINK, raw)
        # plink must remain the landed Autopsy checkout (no remint)
        self.assertEqual(raw.count("buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g"), 2)

    def test_receipt(self) -> None:
        self.assertTrue(RECEIPT.is_file(), RECEIPT)
        body = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("forge-autopsy-postpay-receipt-handoff-20260906-01", body)
        self.assertIn("#8802", body)
        self.assertIn("No remint", body)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
