#!/usr/bin/env python3
"""Hermetic: equipment diagnostic_contract_card + diagnostic_receipt_card."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from integrations.shared_equipment.peers import GrokBotEquipment

_FIXTURES = (
    Path(__file__).resolve().parents[1]
    / "transferable_roles"
    / "fixtures"
)
DIAG = _FIXTURES / "synthetic_diagnostic_fulfillment_role.json"
CRM = _FIXTURES / "synthetic_crm_followup_role.json"


class DiagnosticEquipmentCardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.eq = GrokBotEquipment()
        self.diag = json.loads(DIAG.read_text(encoding="utf-8"))

    def test_contract_card_all_slugs(self) -> None:
        for slug in ("dealer", "referral", "repair", "plant"):
            with self.subTest(slug=slug):
                out = self.eq.call(
                    "diagnostic_contract_card",
                    {"role": self.diag, "slug": slug},
                )
                self.assertTrue(out.get("ok"), out)
                card = out["card"]
                self.assertEqual(card["slug"], slug)
                self.assertTrue(card.get("pointer"))
                self.assertIn("diagnostic_usd", card)

    def test_receipt_card_landed_slugs(self) -> None:
        for slug in ("dealer", "referral", "plant"):
            with self.subTest(slug=slug):
                out = self.eq.call(
                    "diagnostic_receipt_card",
                    {"role": self.diag, "slug": slug},
                )
                self.assertTrue(out.get("ok"), out)
                card = out["card"]
                self.assertEqual(card["slug"], slug)
                self.assertEqual(card.get("cash_usd"), 0)
                self.assertIs(card.get("payment_verified"), False)

    def test_receipt_repair_refuses(self) -> None:
        out = self.eq.call(
            "diagnostic_receipt_card",
            {"role": self.diag, "slug": "repair"},
        )
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("error"), "role_refused")

    def test_crm_role_refuses(self) -> None:
        crm = json.loads(CRM.read_text(encoding="utf-8"))
        for name in ("diagnostic_contract_card", "diagnostic_receipt_card"):
            with self.subTest(name=name):
                out = self.eq.call(name, {"role": crm, "slug": "dealer"})
                self.assertFalse(out.get("ok"))
                self.assertEqual(out.get("error"), "role_refused")

    def test_tools_listed(self) -> None:
        names = {t["name"] for t in self.eq.tools()}
        self.assertIn("diagnostic_contract_card", names)
        self.assertIn("diagnostic_receipt_card", names)


if __name__ == "__main__":
    unittest.main()
