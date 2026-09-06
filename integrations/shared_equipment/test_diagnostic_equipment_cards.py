#!/usr/bin/env python3
"""Hermetic: equipment diagnostic/autopsy contract+receipt+fulfill cards."""

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
AUTOPSY = _FIXTURES / "synthetic_agent_failure_autopsy_role.json"
CRM = _FIXTURES / "synthetic_crm_followup_role.json"

_EVIDENCE = "2026-09-04T15:00:00-04:00"
_AS_OF_OPEN = "2026-09-04T16:00:00-04:00"
_AS_OF_MISSED = "2026-09-08T10:00:00-04:00"


class DiagnosticEquipmentCardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.eq = GrokBotEquipment()
        self.diag = json.loads(DIAG.read_text(encoding="utf-8"))
        self.autopsy = json.loads(AUTOPSY.read_text(encoding="utf-8"))

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

    def test_diagnostic_fulfill_deadline_and_sla(self) -> None:
        due = self.eq.call(
            "diagnostic_fulfill_deadline_card",
            {
                "role": self.diag,
                "slug": "dealer",
                "usable_evidence_at": _EVIDENCE,
            },
        )
        self.assertTrue(due.get("ok"), due)
        self.assertTrue(due["card"].get("delivery_due_at"))
        open_card = self.eq.call(
            "diagnostic_fulfill_sla_card",
            {
                "role": self.diag,
                "slug": "dealer",
                "usable_evidence_at": _EVIDENCE,
                "as_of": _AS_OF_OPEN,
            },
        )
        self.assertTrue(open_card.get("ok"), open_card)
        self.assertEqual(open_card["card"].get("sla_status"), "OPEN")
        missed = self.eq.call(
            "diagnostic_fulfill_sla_card",
            {
                "role": self.diag,
                "slug": "dealer",
                "usable_evidence_at": _EVIDENCE,
                "as_of": _AS_OF_MISSED,
            },
        )
        self.assertTrue(missed.get("ok"), missed)
        self.assertEqual(missed["card"].get("sla_status"), "MISSED")

    def test_autopsy_fulfill_deadline_and_sla(self) -> None:
        due = self.eq.call(
            "autopsy_fulfill_deadline_card",
            {"role": self.autopsy, "usable_evidence_at": _EVIDENCE},
        )
        self.assertTrue(due.get("ok"), due)
        self.assertTrue(due["card"].get("delivery_due_at"))
        open_card = self.eq.call(
            "autopsy_fulfill_sla_card",
            {
                "role": self.autopsy,
                "usable_evidence_at": _EVIDENCE,
                "as_of": _AS_OF_OPEN,
            },
        )
        self.assertTrue(open_card.get("ok"), open_card)
        self.assertEqual(open_card["card"].get("sla_status"), "OPEN")
        missed = self.eq.call(
            "autopsy_fulfill_sla_card",
            {
                "role": self.autopsy,
                "usable_evidence_at": _EVIDENCE,
                "as_of": _AS_OF_MISSED,
            },
        )
        self.assertTrue(missed.get("ok"), missed)
        self.assertEqual(missed["card"].get("sla_status"), "MISSED")

    def test_crm_role_refuses(self) -> None:
        crm = json.loads(CRM.read_text(encoding="utf-8"))
        cases = [
            ("diagnostic_contract_card", {"role": crm, "slug": "dealer"}),
            ("diagnostic_receipt_card", {"role": crm, "slug": "dealer"}),
            (
                "diagnostic_fulfill_deadline_card",
                {
                    "role": crm,
                    "slug": "dealer",
                    "usable_evidence_at": _EVIDENCE,
                },
            ),
            (
                "autopsy_fulfill_deadline_card",
                {"role": crm, "usable_evidence_at": _EVIDENCE},
            ),
        ]
        for name, args in cases:
            with self.subTest(name=name):
                out = self.eq.call(name, args)
                self.assertFalse(out.get("ok"))
                self.assertEqual(out.get("error"), "role_refused")

    def test_tools_listed(self) -> None:
        names = {t["name"] for t in self.eq.tools()}
        for name in (
            "diagnostic_contract_card",
            "diagnostic_receipt_card",
            "diagnostic_fulfill_deadline_card",
            "diagnostic_fulfill_sla_card",
            "autopsy_fulfill_deadline_card",
            "autopsy_fulfill_sla_card",
        ):
            self.assertIn(name, names)


if __name__ == "__main__":
    unittest.main()
