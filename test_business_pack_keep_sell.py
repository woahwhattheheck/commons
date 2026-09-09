#!/usr/bin/env python3
"""Contracts for the KEEP vs SELL factory.

Does not steal the pack-scaffold landing. Marketing stays Bryce.
No invented Stripe URLs, buyers, cash, or ad spend.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "ground" / "BUSINESS_PACK_KEEP_SELL.json"
CARD = ROOT / "ground" / "BUSINESS_PACK_KEEP_SELL.md"
DOOR = ROOT / "keep-sell.html"
CONTROL_PLANE = ROOT / "ground" / "SLACK_CONTROL_PLANE.json"


def load_mod():
    spec = importlib.util.spec_from_file_location(
        "business_pack_keep_sell", ROOT / "host" / "business_pack_keep_sell.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


MOD = load_mod()


class BusinessPackKeepSellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = MOD
        cls.ledger = cls.mod.load_ledger(LEDGER)
        cls.card = CARD.read_text(encoding="utf-8")
        cls.door = DOOR.read_text(encoding="utf-8")
        cls.control = json.loads(CONTROL_PLANE.read_text(encoding="utf-8"))

    def test_live_ledger_is_valid_and_empty(self):
        self.assertEqual(self.mod.validate_ledger(self.ledger), [])
        self.assertEqual(self.ledger["kind"], "BUSINESS_PACK_KEEP_SELL_FACTORY")
        self.assertEqual(self.ledger["packs"], [])
        self.assertEqual(self.ledger["cash_usd"], "0.00")
        self.assertEqual(self.ledger["buyers"], 0)
        self.assertEqual(self.ledger["marketing"], "BRYCE")
        self.assertIs(self.ledger["scaffold_not_stolen"], True)
        self.assertEqual(self.ledger["slack_channel"]["id"], "C0BU7JAPUH3")

    def test_does_not_steal_control_plane_or_scaffold_paths(self):
        self.assertEqual(self.control["channels"]["business_packs"]["id"], "C0BU7JAPUH3")
        self.assertEqual(self.ledger["control_plane_receipt"], "cursor-slack-business-packs-channel-20260902-01")
        self.assertNotEqual(LEDGER.name, "SLACK_CONTROL_PLANE.json")
        self.assertNotEqual(LEDGER.name, "BUSINESS_PACKS.json")
        self.assertNotEqual(DOOR.name, "business-packs.html")
        self.assertIn("does not steal", self.card.lower())
        self.assertIn("BUSINESS_PACKS.md", self.card)

    def test_record_keep_and_sell(self):
        ledger = self.mod.empty_ledger()
        keep = self.mod.record_decision(
            ledger, pack_id="keep-demo-pack-20260902-01", decision="KEEP",
            title="Keep this winner", tier_usd=100,
        )
        sell = self.mod.record_decision(
            ledger, pack_id="sell-demo-pack-20260902-01", decision="SELL",
            title="Sell this package", tier_usd=200,
        )
        self.assertEqual(keep["decision"], "KEEP")
        self.assertEqual(sell["decision"], "SELL")
        self.assertEqual(keep["marketing"], "BRYCE")
        self.assertEqual(self.mod.validate_ledger(ledger), [])

    def test_rejects_invented_and_lookalike_checkout(self):
        ledger = self.mod.empty_ledger()
        self.mod.record_decision(
            ledger, pack_id="sell-demo-pack-20260902-01", decision="SELL",
            title="Sell this package",
        )
        with self.assertRaises(ValueError):
            self.mod.set_checkout(
                ledger, pack_id="sell-demo-pack-20260902-01",
                url="https://buy.stripe.com/invented", owner_pasted=False,
            )
        with self.assertRaises(ValueError):
            self.mod.set_checkout(
                ledger, pack_id="sell-demo-pack-20260902-01",
                url="https://buy.stripe.com.evil.test/x", owner_pasted=True,
            )
        with self.assertRaises(ValueError):
            self.mod.set_checkout(
                ledger, pack_id="sell-demo-pack-20260902-01",
                url="https://example.com/not-stripe", owner_pasted=True,
            )

    def test_owner_pasted_link_stays_inert_until_chargeable(self):
        ledger = self.mod.empty_ledger()
        self.mod.record_decision(
            ledger, pack_id="sell-demo-pack-20260902-01", decision="SELL",
            title="Sell this package",
        )
        self.mod.set_checkout(
            ledger, pack_id="sell-demo-pack-20260902-01",
            url="https://buy.stripe.com/14kQexample", owner_pasted=True,
        )
        self.assertEqual(self.mod.validate_ledger(ledger), [])
        public = self.mod.render_public_rows(ledger)
        self.assertEqual(public[0]["checkout_href"], "")
        self.assertEqual(public[0]["checkout_state"], "OWNER_PASTED_NOT_CHARGEABLE")
        live = self.mod.render_public_rows(ledger, {"https://buy.stripe.com/14kQexample"})
        self.assertEqual(live[0]["checkout_href"], "https://buy.stripe.com/14kQexample")

    def test_rejects_agent_ad_spend_and_marketing_reassign(self):
        ledger = self.mod.empty_ledger()
        self.mod.record_decision(
            ledger, pack_id="keep-demo-pack-20260902-01", decision="KEEP",
            title="Keep this winner",
        )
        ledger["packs"][0]["ad_spend"] = True
        ledger["packs"][0]["marketing"] = "AGENT"
        errors = self.mod.validate_ledger(ledger)
        self.assertTrue(any("ad spend" in err for err in errors))
        self.assertTrue(any("marketing" in err for err in errors))

    def test_door_has_no_stripe_href_and_names_the_lane(self):
        self.assertNotIn("buy.stripe.com", self.door)
        self.assertNotIn('href="https://buy.stripe.com', self.door)
        self.assertIn("C0BU7JAPUH3", self.door)
        self.assertIn("NEED_OWNER_LINK", self.door)
        self.assertIn("Bryce only", self.door)
        self.assertIn("keep-sell.html", self.card)

    def test_cli_validate_and_self_test(self):
        self.assertEqual(self.mod.main(["validate"]), 0)
        self.assertEqual(self.mod.main(["list"]), 0)
        self.assertEqual(self.mod.self_test(), 0)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            self.mod.write_ledger(self.mod.empty_ledger(), path)
            self.assertEqual(self.mod.main(["--ledger", str(path), "record", "--id", "cli-keep-pack-20260902-01", "--decision", "KEEP", "--title", "CLI keep", "--tier", "20"]), 0)
            loaded = self.mod.load_ledger(path)
            self.assertEqual(loaded["packs"][0]["decision"], "KEEP")


if __name__ == "__main__":
    unittest.main()
