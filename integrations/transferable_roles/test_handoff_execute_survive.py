#!/usr/bin/env python3
"""Hermetic: role-gated executes survive transfer and export→import."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from handoff_execute import prove_successor_executes
from roles import RoleError, RoleStore
import cli as roles_cli

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CRM = FIXTURES / "synthetic_crm_followup_role.json"
AUTOPSY = FIXTURES / "synthetic_agent_failure_autopsy_role.json"
DIAG = FIXTURES / "synthetic_diagnostic_fulfillment_role.json"


class HandoffExecuteSurviveTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = RoleStore(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_autopsy_transfer_then_prove(self) -> None:
        role = self.store.create(json.loads(AUTOPSY.read_text(encoding="utf-8")))
        rid = role["role_id"]
        self.store.bind_access_route(
            rid,
            route_name="grokbot_control_g2",
            session_id="g2-handoff-sess",
            last_run_id="g2-handoff-run",
        )
        self.store.equip(rid, session_id="sess-A", harness="hinge", seat="HINGE")
        self.store.transfer(
            rid,
            from_session_id="sess-A",
            to_session_id="sess-B",
            to_harness="rivet",
            seat="RIVET",
        )
        proof = prove_successor_executes(self.store, rid)
        self.assertTrue(proof["ok"])
        self.assertEqual(proof["occupant_session"], "sess-B")
        self.assertIn("autopsy-case", proof["executes"])
        self.assertIn("autopsy-receipt-row", proof["executes"])
        self.assertIn("autopsy-fulfill-deadline", proof["executes"])
        self.assertIn("autopsy-fulfill-validate", proof["executes"])
        g2 = next(r for r in proof["bound_routes"] if r["name"] == "grokbot_control_g2")
        self.assertEqual(g2["session_id"], "g2-handoff-sess")
        self.assertEqual(g2["last_run_id"], "g2-handoff-run")

    def test_autopsy_export_import_then_prove(self) -> None:
        role = self.store.create(json.loads(AUTOPSY.read_text(encoding="utf-8")))
        rid = role["role_id"]
        self.store.bind_access_route(
            rid,
            route_name="grokbot_control_g2",
            session_id="g2-export-sess",
            last_run_id="g2-export-run",
        )
        self.store.equip(rid, session_id="occ-export", harness="hinge")
        package = self.store.export_package(rid)
        with tempfile.TemporaryDirectory() as fresh_dir:
            fresh = RoleStore(fresh_dir)
            imported = fresh.import_package(package)
            fresh.equip(
                imported["role_id"],
                session_id="occ-import",
                harness="rivet",
                seat="RIVET",
            )
            proof = prove_successor_executes(fresh, imported["role_id"])
            self.assertTrue(proof["ok"])
            self.assertEqual(proof["occupant_session"], "occ-import")
            self.assertIn("autopsy-case", proof["executes"])
            g2 = next(
                r for r in proof["bound_routes"] if r["name"] == "grokbot_control_g2"
            )
            self.assertEqual(g2["session_id"], "g2-export-sess")

    def test_diagnostic_transfer_then_prove(self) -> None:
        role = self.store.create(json.loads(DIAG.read_text(encoding="utf-8")))
        rid = role["role_id"]
        self.store.equip(rid, session_id="d-A", harness="hinge")
        self.store.transfer(
            rid,
            from_session_id="d-A",
            to_session_id="d-B",
            to_harness="rivet",
        )
        proof = prove_successor_executes(self.store, rid, diagnostic_slug="dealer")
        self.assertTrue(proof["ok"])
        self.assertIn("diagnostic-contract", proof["executes"])
        self.assertEqual(proof["executes"]["diagnostic-contract"]["slug"], "dealer")

    def test_crm_refuses(self) -> None:
        role = self.store.create(json.loads(CRM.read_text(encoding="utf-8")))
        with self.assertRaises(RoleError):
            prove_successor_executes(self.store, role["role_id"])

    def test_cli_prove_handoff(self) -> None:
        store_dir = self._tmp.name
        with redirect_stdout(io.StringIO()):
            rc = roles_cli.main(
                ["--store", store_dir, "create", "--file", str(AUTOPSY)]
            )
        self.assertEqual(rc, 0)
        rid = "role-synthetic-agent-failure-autopsy-20260905"
        with redirect_stdout(io.StringIO()):
            rc = roles_cli.main(
                [
                    "--store",
                    store_dir,
                    "equip",
                    rid,
                    "--session",
                    "cli-A",
                    "--harness",
                    "hinge",
                ]
            )
        self.assertEqual(rc, 0)
        cli = FIXTURES.parent / "cli.py"
        result = subprocess.run(
            [
                sys.executable,
                str(cli),
                "prove-handoff",
                rid,
                "--store",
                store_dir,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        proof = json.loads(result.stdout)
        self.assertTrue(proof["ok"])
        self.assertIn("autopsy-case", proof["executes"])


if __name__ == "__main__":
    unittest.main()
