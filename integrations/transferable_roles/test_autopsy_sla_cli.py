#!/usr/bin/env python3
"""Hermetic: Autopsy R4 CLI executes SLA OPEN|MISSED vs as_of."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from autopsy_fulfill import run_sla_status
from roles import RoleError, RoleStore

FIXTURES = Path(__file__).resolve().parent / "fixtures"
AUTOPSY = FIXTURES / "synthetic_agent_failure_autopsy_role.json"
DIAG = FIXTURES / "synthetic_diagnostic_fulfillment_role.json"
CRM = FIXTURES / "synthetic_crm_followup_role.json"


class AutopsySlaCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = RoleStore(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_open_before_deadline_and_missed_after(self) -> None:
        role = self.store.create(json.loads(AUTOPSY.read_text(encoding="utf-8")))
        stamp = "2026-09-04T15:00:00-04:00"  # Friday → due Mon 15:00
        open_card = run_sla_status(
            role,
            usable_evidence_at=stamp,
            as_of="2026-09-07T14:59:59-04:00",
        )
        self.assertEqual(open_card["delivery_due_at"], "2026-09-07T15:00:00-04:00")
        self.assertEqual(open_card["sla_status"], "OPEN")
        self.assertTrue(open_card["within_one_business_day"])
        self.assertIn("refund usd 29", str(open_card["refund"]).lower())
        self.assertIn("one-business-day", str(open_card["refund"]).lower())
        self.assertEqual(open_card["amount_usd"], 29)

        edge = run_sla_status(
            role,
            usable_evidence_at=stamp,
            as_of="2026-09-07T15:00:00-04:00",
        )
        self.assertEqual(edge["sla_status"], "OPEN")
        self.assertTrue(edge["within_one_business_day"])
        self.assertIn("refund usd 29", str(edge["refund"]).lower())
        self.assertEqual(edge["amount_usd"], 29)

        missed = run_sla_status(
            role,
            usable_evidence_at=stamp,
            as_of="2026-09-07T15:00:01-04:00",
        )
        self.assertEqual(missed["sla_status"], "MISSED")
        self.assertFalse(missed["within_one_business_day"])
        self.assertIn("refund usd 29", str(missed["refund"]).lower())
        self.assertEqual(missed["amount_usd"], 29)

    def test_diagnostic_and_crm_refuse(self) -> None:
        diagnostic = self.store.create(json.loads(DIAG.read_text(encoding="utf-8")))
        crm = self.store.create(json.loads(CRM.read_text(encoding="utf-8")))
        with self.assertRaises(RoleError):
            run_sla_status(
                diagnostic,
                usable_evidence_at="2026-09-04T15:00:00-04:00",
                as_of="2026-09-07T12:00:00-04:00",
            )
        with self.assertRaises(RoleError):
            run_sla_status(
                crm,
                usable_evidence_at="2026-09-04T15:00:00-04:00",
                as_of="2026-09-07T12:00:00-04:00",
            )

    def test_documented_command_runs_without_equipping(self) -> None:
        role = self.store.create(json.loads(AUTOPSY.read_text(encoding="utf-8")))
        self.assertIsNone(role["occupant"])
        before = {p.name: p.read_bytes() for p in Path(self._tmp.name).glob("*.json")}
        result = subprocess.run(
            [
                sys.executable,
                str(FIXTURES.parent / "cli.py"),
                "autopsy-fulfill-sla",
                role["role_id"],
                "--usable-evidence-at",
                "2026-09-04T15:00:00-04:00",
                "--as-of",
                "2026-09-08T10:00:00-04:00",
                "--store",
                self._tmp.name,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        out = json.loads(result.stdout)
        self.assertEqual(out["sla_status"], "MISSED")
        self.assertFalse(out["within_one_business_day"])
        self.assertIn("refund usd 29", str(out["refund"]).lower())
        self.assertEqual(out["amount_usd"], 29)
        after = {p.name: p.read_bytes() for p in Path(self._tmp.name).glob("*.json")}
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
