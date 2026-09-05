#!/usr/bin/env python3
"""Hermetic: diagnostic role loads landed contract.json by slug via CLI glue."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from diagnostic_contract import (
    SLUG_TO_CONTRACT,
    load_contract_from_role,
    require_diagnostic_contract_tool,
)
from roles import RoleError, RoleStore

FIXTURES = Path(__file__).resolve().parent / "fixtures"
DIAG = FIXTURES / "synthetic_diagnostic_fulfillment_role.json"
CRM = FIXTURES / "synthetic_crm_followup_role.json"
AUTOPSY = FIXTURES / "synthetic_agent_failure_autopsy_role.json"


class DiagnosticContractCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = RoleStore(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_diagnostic_role_loads_each_slug(self) -> None:
        role = self.store.create(json.loads(DIAG.read_text(encoding="utf-8")))
        tool = require_diagnostic_contract_tool(role)
        self.assertEqual(tool["name"], "diagnostic_contract")
        for slug, pointer in SLUG_TO_CONTRACT.items():
            card = load_contract_from_role(role, slug=slug)
            self.assertEqual(card["slug"], slug)
            self.assertEqual(card["pointer"], pointer)
            self.assertTrue(card["id"])
            self.assertEqual(card["diagnostic_usd"], 199)
            self.assertIn("one business day", str(card.get("diagnostic_window") or ""))

    def test_crm_and_autopsy_refuse(self) -> None:
        crm = self.store.create(json.loads(CRM.read_text(encoding="utf-8")))
        autopsy = self.store.create(json.loads(AUTOPSY.read_text(encoding="utf-8")))
        with self.assertRaises(RoleError):
            require_diagnostic_contract_tool(crm)
        with self.assertRaises(RoleError):
            load_contract_from_role(autopsy, slug="dealer")

    def test_unknown_slug_refuses(self) -> None:
        role = self.store.create(json.loads(DIAG.read_text(encoding="utf-8")))
        with self.assertRaises(RoleError):
            load_contract_from_role(role, slug="not-a-slug")


if __name__ == "__main__":
    unittest.main()
