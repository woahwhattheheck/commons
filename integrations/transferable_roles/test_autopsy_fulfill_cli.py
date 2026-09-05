#!/usr/bin/env python3
"""Hermetic: Autopsy R4 CLI executes landed fulfillment deadline + validate."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from autopsy_fulfill import (
    require_autopsy_fulfillment_tool,
    run_deadline,
    run_validate,
)
from roles import RoleError, RoleStore

FIXTURES = Path(__file__).resolve().parent / "fixtures"
AUTOPSY = FIXTURES / "synthetic_agent_failure_autopsy_role.json"
CRM = FIXTURES / "synthetic_crm_followup_role.json"
DIAG = FIXTURES / "synthetic_diagnostic_fulfillment_role.json"


class AutopsyFulfillCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = RoleStore(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_autopsy_deadline_executes(self) -> None:
        role = self.store.create(json.loads(AUTOPSY.read_text(encoding="utf-8")))
        tool = require_autopsy_fulfillment_tool(role)
        self.assertEqual(tool["name"], "autopsy_fulfillment")
        out = run_deadline(
            role, usable_evidence_at="2026-09-04T15:00:00-04:00"
        )
        self.assertEqual(out["usable_evidence_at"], "2026-09-04T15:00:00-04:00")
        self.assertIn("delivery_due_at", out)
        # Friday 15:00 ET → Monday same wall clock.
        self.assertTrue(out["delivery_due_at"].startswith("2026-09-07T15:00:00"))

    def test_autopsy_validate_examples(self) -> None:
        role = self.store.create(json.loads(AUTOPSY.read_text(encoding="utf-8")))
        result = run_validate(role)
        self.assertTrue(result.get("ok"))
        self.assertIn("case_id", result)
        self.assertIn("disposition", result)

    def test_crm_and_diagnostic_refuse(self) -> None:
        crm = self.store.create(json.loads(CRM.read_text(encoding="utf-8")))
        diag = self.store.create(json.loads(DIAG.read_text(encoding="utf-8")))
        with self.assertRaises(RoleError):
            require_autopsy_fulfillment_tool(crm)
        with self.assertRaises(RoleError):
            run_deadline(diag, usable_evidence_at="2026-09-04T15:00:00-04:00")


    def test_documented_commands_run_without_equipping(self) -> None:
        role = self.store.create(json.loads(AUTOPSY.read_text(encoding="utf-8")))
        self.assertIsNone(role["occupant"])
        before = self.store.get(role["role_id"])
        results = []
        for command, options in [
            ("autopsy-fulfill-deadline",
             ["--usable-evidence-at", "2026-09-04T15:00:00-04:00"]),
            ("autopsy-fulfill-validate", []),
        ]:
            result = subprocess.run(
                [sys.executable, str(FIXTURES.parent / "cli.py"), command,
                 role["role_id"], *options, "--store", self._tmp.name],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            results.append(json.loads(result.stdout))
        self.assertEqual(results[0]["delivery_due_at"], "2026-09-07T15:00:00-04:00")
        self.assertTrue(results[1]["ok"])
        self.assertEqual(results[1]["artifact_state"], "PEER_DRAFT")
        self.assertEqual(self.store.get(role["role_id"]), before)


if __name__ == "__main__":
    unittest.main()
