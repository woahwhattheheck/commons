#!/usr/bin/env python3
"""Hermetic: equipment prove_handoff_card (HINGE CLAIM)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from integrations.shared_equipment.peers import GrokBotEquipment

_FIXTURES = (
    Path(__file__).resolve().parents[1]
    / "transferable_roles"
    / "fixtures"
)
_TR = Path(__file__).resolve().parents[1] / "transferable_roles"
if str(_TR) not in sys.path:
    sys.path.insert(0, str(_TR))

DIAG = _FIXTURES / "synthetic_diagnostic_fulfillment_role.json"
AUTOPSY = _FIXTURES / "synthetic_agent_failure_autopsy_role.json"
CRM = _FIXTURES / "synthetic_crm_followup_role.json"

_EVIDENCE = "2026-09-04T15:00:00-04:00"
_AS_OF_OPEN = "2026-09-04T16:00:00-04:00"


class ProveHandoffEquipmentCardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.eq = GrokBotEquipment()
        self.diag = json.loads(DIAG.read_text(encoding="utf-8"))
        self.autopsy = json.loads(AUTOPSY.read_text(encoding="utf-8"))

    def test_prove_handoff_card_diagnostic(self) -> None:
        # hinge-r4-equipment-prove-handoff-card-20260906-01
        out = self.eq.call(
            "prove_handoff_card",
            {
                "role": self.diag,
                "slug": "dealer",
                "usable_evidence_at": _EVIDENCE,
                "as_of": _AS_OF_OPEN,
            },
        )
        self.assertTrue(out.get("ok"), out)
        proof = out["proof"]
        self.assertTrue(proof.get("ok"))
        self.assertIn("diagnostic-fulfill-sla", proof["executes"])
        sla = proof["executes"]["diagnostic-fulfill-sla"]
        self.assertEqual(sla.get("sla_status"), "OPEN")
        self.assertEqual(sla.get("diagnostic_usd"), 199)

    def test_prove_handoff_card_autopsy(self) -> None:
        # hinge-r4-equipment-prove-handoff-card-20260906-01
        out = self.eq.call(
            "prove_handoff_card",
            {
                "role": self.autopsy,
                "usable_evidence_at": _EVIDENCE,
                "as_of": _AS_OF_OPEN,
            },
        )
        self.assertTrue(out.get("ok"), out)
        proof = out["proof"]
        self.assertTrue(proof.get("ok"))
        self.assertIn("autopsy-fulfill-sla", proof["executes"])
        sla = proof["executes"]["autopsy-fulfill-sla"]
        self.assertEqual(sla.get("sla_status"), "OPEN")
        self.assertEqual(sla.get("amount_usd"), 29)

    def test_prove_handoff_card_crm_refuses(self) -> None:
        crm = json.loads(CRM.read_text(encoding="utf-8"))
        out = self.eq.call("prove_handoff_card", {"role": crm})
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("error"), "role_refused")

    def test_prove_handoff_card_listed(self) -> None:
        names = {t["name"] for t in self.eq.tools()}
        self.assertIn("prove_handoff_card", names)


if __name__ == "__main__":
    unittest.main()
