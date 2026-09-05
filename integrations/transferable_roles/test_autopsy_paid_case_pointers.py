#!/usr/bin/env python3
"""Hermetic: Autopsy R4 fixture points at paid_case.py (SPARK #8961)."""

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


class AutopsyPaidCasePointerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = RoleStore(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_autopsy_fixture_points_at_paid_case(self) -> None:
        raw = json.loads(AUTOPSY_FIXTURE.read_text(encoding="utf-8"))
        role = self.store.create(raw)
        pointers = {k["pointer"] for k in role["knowledge"]}
        self.assertIn(PAID_CASE, pointers)
        tools = {t["name"]: t for t in role["tools"]}
        self.assertIn("autopsy_paid_case", tools)
        self.assertEqual(tools["autopsy_paid_case"]["entry"], PAID_CASE)
        notes = tools["autopsy_paid_case"].get("notes", "")
        self.assertIn("case_from_autopsy_offer", notes)
        g2 = next(r for r in role["access_routes"] if r["name"] == "grokbot_control_g2")
        self.assertIn("paid_case", g2.get("note", ""))
        blob = json.dumps(role)
        self.assertIn(LIVE_CHECKOUT, blob)
        for forbidden in ("prod_", "price_", "plink_", "acct_"):
            self.assertNotIn(forbidden, blob)


if __name__ == "__main__":
    unittest.main()
