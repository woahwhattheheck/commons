#!/usr/bin/env python3
"""Hermetic: Autopsy R4 fixture cites receipt_row_from_case (SPARK #8967)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from roles import RoleStore

AUTOPSY_FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "synthetic_agent_failure_autopsy_role.json"
)
PAID_CASE = "integrations/grokbot_control/paid_case.py"
LIVE_CHECKOUT = "buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g"


class AutopsyReceiptRowPointerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = RoleStore(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_autopsy_fixture_cites_receipt_row_from_case(self) -> None:
        raw = json.loads(AUTOPSY_FIXTURE.read_text(encoding="utf-8"))
        role = self.store.create(raw)
        paid = next(k for k in role["knowledge"] if k["pointer"] == PAID_CASE)
        self.assertIn("receipt_row_from_case", paid.get("label", ""))
        tools = {t["name"]: t for t in role["tools"]}
        self.assertIn("autopsy_paid_case", tools)
        notes = tools["autopsy_paid_case"].get("notes", "")
        self.assertIn("receipt_row_from_case", notes)
        self.assertIn("REAL_STRIPE_PAYMENT_OBSERVED", notes)
        seats = next(
            k for k in role["knowledge"] if k["pointer"].endswith("seats.json")
        )
        self.assertIn("case_row_shape", seats.get("label", ""))
        g2 = next(r for r in role["access_routes"] if r["name"] == "grokbot_control_g2")
        self.assertIn("receipt_row_from_case", g2.get("note", ""))
        blob = json.dumps(role)
        self.assertIn(LIVE_CHECKOUT, blob)
        for forbidden in ("prod_", "price_", "plink_", "acct_"):
            self.assertNotIn(forbidden, blob)


if __name__ == "__main__":
    unittest.main()
