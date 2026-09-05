#!/usr/bin/env python3
"""Hermetic: diagnostic role loads landed receipt.json by slug (TENON claim)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from diagnostic_receipt import (
    SLUG_TO_RECEIPT_JSON,
    load_receipt_from_role,
    require_diagnostic_receipt_tool,
)
from roles import RoleError, RoleStore

FIXTURES = Path(__file__).resolve().parent / "fixtures"
DIAG = FIXTURES / "synthetic_diagnostic_fulfillment_role.json"
CRM = FIXTURES / "synthetic_crm_followup_role.json"


class DiagnosticReceiptCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = RoleStore(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_diagnostic_role_loads_each_receipt_slug(self) -> None:
        role = self.store.create(json.loads(DIAG.read_text(encoding="utf-8")))
        tool = require_diagnostic_receipt_tool(role)
        self.assertEqual(tool["name"], "diagnostic_receipt")
        for slug, pointer in SLUG_TO_RECEIPT_JSON.items():
            card = load_receipt_from_role(role, slug=slug)
            self.assertEqual(card["slug"], slug)
            self.assertEqual(card["pointer"], pointer)
            self.assertTrue(card.get("receipt_id"))
            self.assertEqual(card.get("cash_usd"), 0)
            self.assertIs(card.get("payment_verified"), False)

    def test_repair_refuses_invent(self) -> None:
        role = self.store.create(json.loads(DIAG.read_text(encoding="utf-8")))
        with self.assertRaises(RoleError):
            load_receipt_from_role(role, slug="repair")

    def test_crm_refuses(self) -> None:
        crm = self.store.create(json.loads(CRM.read_text(encoding="utf-8")))
        with self.assertRaises(RoleError):
            require_diagnostic_receipt_tool(crm)


if __name__ == "__main__":
    unittest.main()
