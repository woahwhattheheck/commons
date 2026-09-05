#!/usr/bin/env python3
"""Hermetic: Autopsy R4 CLI builds G2 case + receipt_row via SPARK helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from autopsy_paid import (
    build_g2_case_from_role,
    build_receipt_row_from_role,
    require_autopsy_paid_tool,
)
from roles import RoleError, RoleStore

FIXTURES = Path(__file__).resolve().parent / "fixtures"
AUTOPSY = FIXTURES / "synthetic_agent_failure_autopsy_role.json"
CRM = FIXTURES / "synthetic_crm_followup_role.json"


class AutopsyCaseCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = RoleStore(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_autopsy_role_builds_g2_case(self) -> None:
        role = self.store.create(json.loads(AUTOPSY.read_text(encoding="utf-8")))
        tool = require_autopsy_paid_tool(role)
        self.assertEqual(tool["name"], "autopsy_paid_case")
        case = build_g2_case_from_role(role, case_ref="case_hermetic_001")
        self.assertEqual(case["case_ref"], "case_hermetic_001")
        self.assertIn("offer_id", case)
        self.assertIn("sku", case)
        for forbidden in ("email", "token", "prod_", "price_", "plink_"):
            self.assertNotIn(forbidden, json.dumps(case))

    def test_autopsy_role_builds_receipt_row(self) -> None:
        role = self.store.create(json.loads(AUTOPSY.read_text(encoding="utf-8")))
        row = build_receipt_row_from_role(
            role,
            case_ref="case_hermetic_002",
            g2_run_id="run_abc",
            g2_session_id="sess_xyz",
            state="UNVERIFIED",
        )
        for key in ("offer_id", "case_ref", "sku", "state"):
            self.assertIn(key, row)
        self.assertEqual(row["case_ref"], "case_hermetic_002")
        self.assertEqual(row["state"], "UNVERIFIED")
        self.assertEqual(row["g2_run_id"], "run_abc")
        self.assertEqual(row["g2_session_id"], "sess_xyz")

    def test_crm_role_refuses_autopsy_case(self) -> None:
        role = self.store.create(json.loads(CRM.read_text(encoding="utf-8")))
        with self.assertRaises(RoleError):
            require_autopsy_paid_tool(role)
        with self.assertRaises(RoleError):
            build_g2_case_from_role(role, case_ref="should_fail")


if __name__ == "__main__":
    unittest.main()
