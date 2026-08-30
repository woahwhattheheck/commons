#!/usr/bin/env python3
"""Keep the public survival checkout aligned with its manual-capture boundary."""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CHECKOUT_URL = "https://buy.stripe.com/8x25kC3Ot9fj5ep1Oy43S0a"
PRODUCT_ID = "prod_VANEgGPRVMVZLJ"
PRICE_ID = "price_1UA2UMATH4EDE7XDGuL1POjW"
PAYMENT_LINK_ID = "plink_1UA2ZuATH4EDE7XDZUJ9wx1k"


class AgentRescueCheckoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = (ROOT / "agent-rescue.html").read_text(encoding="utf-8")
        cls.sku = (ROOT / "land" / "sku-agent-survival-proof-20260830.md").read_text(encoding="utf-8")
        cls.acceptance = (ROOT / "revenue" / "production_survival" / "acceptance_contract.md").read_text(encoding="utf-8")
        cls.handoff = (ROOT / "revenue" / "payment_ready" / "processor_handoff.md").read_text(encoding="utf-8")

    def test_exact_live_checkout_is_public_once(self):
        self.assertEqual(self.page.count('href="' + CHECKOUT_URL + '"'), 1)
        self.assertIn("Authorize one proof — $2,500", self.page)
        for marker in (
            "status: ACTIVE_CHARGEABLE",
            "checkout: `" + CHECKOUT_URL + "`",
            "checkout_url: `" + CHECKOUT_URL + "`",
            "product_id: `" + PRODUCT_ID + "`",
            "price_id: `" + PRICE_ID + "`",
            "payment_link_id: `" + PAYMENT_LINK_ID + "`",
            "capture_method: manual",
            "payment_methods: dynamic",
            "completed_sessions_count: 0",
            "completed_sessions_limit: 1",
        ):
            self.assertIn(marker, self.sku)

    def test_buyer_copy_preserves_authorization_and_capacity_boundary(self):
        combined = "\n".join((self.page, self.acceptance, self.handoff, self.sku)).lower()
        for marker in (
            "before capture",
            "bad-fit",
            "one buyer at a time",
            "authorization is not capture",
            "authorization != capture != settlement != payout != bank_available",
            "collected cash remains usd 0",
        ):
            self.assertIn(marker, combined)
        self.assertIn("required non-confidential failure sentence", combined)
        self.assertIn("optional public", combined)

    def test_public_files_contain_no_secret_key_shape(self):
        combined = "\n".join((self.page, self.acceptance, self.handoff, self.sku))
        self.assertIsNone(re.search(r"(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{12,}", combined))
        self.assertNotRegex(CHECKOUT_URL, r"[?#]")


if __name__ == "__main__":
    unittest.main()
