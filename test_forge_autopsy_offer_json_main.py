#!/usr/bin/env python3
"""Hermetic pin: LIVE_VERIFIED Autopsy offer.json on main."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OFFER = ROOT / "revenue" / "agent_failure_autopsy" / "offer.json"
LIVE_URL = "https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g"


class TestForgeAutopsyOfferJsonMain(unittest.TestCase):
    def test_offer_json_is_live_verified(self) -> None:
        self.assertTrue(OFFER.is_file(), "offer.json missing")
        raw = OFFER.read_text(encoding="utf-8")
        data = json.loads(raw)
        self.assertEqual(data["offer_id"], "agent-failure-autopsy-29")
        self.assertEqual(data["status"], "ACTIVE_VERIFIED")
        price = data["price"]
        self.assertEqual(price["amount"], 29)
        self.assertEqual(price["payment_url"], LIVE_URL)
        self.assertEqual(price["payment_url_state"], "LIVE_VERIFIED")
        self.assertEqual(price["provider_product_id"], "prod_VCevsvv7skWk3e")
        self.assertEqual(price["provider_price_id"], "price_1UCFbHATH4EDE7XD4NNrjfUe")
        self.assertEqual(price["provider_payment_link_id"], "plink_1UCFbLATH4EDE7XDlTunr6iO")
        self.assertNotIn("sk_live", raw)
        self.assertNotIn("sk_test", raw)


if __name__ == "__main__":
    unittest.main()
