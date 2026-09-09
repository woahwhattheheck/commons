#!/usr/bin/env python3
"""Shared pack thank-you door: empty pixel slot loads no third-party scripts."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_thanks as thanks  # noqa: E402


class BusinessPackThanksTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = thanks.load_law()
        self.door = (ROOT / "packs" / "thanks.html").read_text(encoding="utf-8")
        self.checkout = (ROOT / "packs" / "_template" / "checkout.md").read_text(
            encoding="utf-8"
        )
        self.template = (ROOT / "land" / "business-pack-template-20260902.md").read_text(
            encoding="utf-8"
        )

    def test_slot_empty_on_main_law(self) -> None:
        self.assertEqual(self.law["id"], "cursor-business-pack-thanks-pixel-20260902-01")
        self.assertEqual(self.law["pixel_id"], "")
        self.assertEqual(self.law["pixel_slot"], "owner_paste")
        self.assertIs(self.law["gate"], False)
        self.assertIs(self.law["commons_admission"], False)
        self.assertIs(self.law["agents_mint_pixel_id"], False)
        self.assertIs(self.law["agents_spend_ads"], False)
        self.assertIs(self.law["empty_loads_zero_third_party_scripts"], True)
        self.assertEqual(
            self.law["scout_demand_id"],
            "scout-demand-pack-door-thanks-pixel-20260902-01",
        )
        self.assertIs(self.law["did_not_remint_scout_demand"], True)
        self.assertEqual(self.law["checkout"], "NOT_MINTED")
        self.assertNotIn("337 NO", json.dumps(self.law))
        self.assertNotIn("337 NO", self.door)

    def test_static_door_has_zero_third_party_scripts(self) -> None:
        result = thanks.classify()
        self.assertEqual(result["verdict"], "PIXEL_SLOT_EMPTY")
        self.assertEqual(result["static_third_party_scripts"], [])
        self.assertTrue(result["empty_loads_zero_third_party_scripts"])
        self.assertEqual(result["would_load_script"], [])
        self.assertNotIn("ads-twitter.com", self.door)
        self.assertNotIn("<script src=", self.door.lower())
        self.assertIn('name="robots"', self.door)
        self.assertIn("index, follow", self.door)
        self.assertIn("password", self.door.lower())
        self.assertNotIn("<form", self.door.lower())
        self.assertNotIn('type="password"', self.door.lower())
        self.assertFalse(result["earnings_claim"])
        self.assertFalse(result["nuts_in_ad_copy"])

    def test_owner_filled_slot_would_load_pixel_and_purchase_value(self) -> None:
        result = thanks.classify(pixel_id="tw-owner-pasted", value="100")
        self.assertEqual(result["verdict"], "PIXEL_SLOT_OWNER_FILLED")
        self.assertTrue(result["pixel_id_present"])
        self.assertEqual(
            result["would_load_script"],
            ["https://static.ads-twitter.com/uwt.js"],
        )
        self.assertEqual(result["purchase"]["event"], "Purchase")
        self.assertEqual(result["purchase"]["value"], 100.0)
        self.assertEqual(result["purchase"]["currency"], "USD")
        self.assertIs(result["agents_spend_ads"], False)
        self.assertIs(result["agents_mint_pixel_id"], False)

    def test_missing_value_does_not_invent_a_price(self) -> None:
        result = thanks.classify(pixel_id="tw-owner-pasted")
        self.assertNotIn("value", result["purchase"])
        self.assertEqual(result["purchase"]["event"], "Purchase")

    def test_template_points_after_payment_redirect_at_thanks_door(self) -> None:
        self.assertIn("packs/thanks.html", self.checkout)
        self.assertIn("after-payment redirect", self.checkout.lower())
        self.assertIn("packs/thanks.html", self.template)
        self.assertIn("BUSINESS_PACK_THANKS.json", self.template)

    def test_cli_empty_slot(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "business_pack_thanks.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verdict"], "PIXEL_SLOT_EMPTY")
        self.assertEqual(payload["law_id"], "cursor-business-pack-thanks-pixel-20260902-01")


if __name__ == "__main__":
    unittest.main()
