#!/usr/bin/env python3
"""Hermetic tests: create → equip A → transfer B; secrets never exported."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from roles import RoleError, RoleStore, SECRET_FIELD_NAMES
import cli as roles_cli

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "synthetic_crm_followup_role.json"


class TransferableRoleTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = RoleStore(self._tmp.name)
        self.raw = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_create_equip_transfer_preserves_purpose_and_next_action(self) -> None:
        role = self.store.create(self.raw)
        role_id = role["role_id"]
        purpose = role["purpose"]
        next_actions = [o["next_action"] for o in role["obligations"]]

        equipped = self.store.equip(
            role_id, session_id="session-A", harness="cursor-hinge", seat="HINGE"
        )
        self.assertEqual(equipped["occupant"]["session_id"], "session-A")
        self.assertEqual(equipped["occupant"]["seat"], "HINGE")
        self.assertEqual(equipped["role_id"], role_id)

        handed = self.store.transfer(
            role_id,
            from_session_id="session-A",
            to_session_id="session-B",
            to_harness="claude-tenon",
            seat="TENON",
        )
        self.assertEqual(handed["role_id"], role_id)
        self.assertEqual(handed["purpose"], purpose)
        self.assertEqual(
            [o["next_action"] for o in handed["obligations"]], next_actions
        )
        self.assertEqual(handed["occupant"]["session_id"], "session-B")
        self.assertEqual(handed["occupant"]["prior_session_id"], "session-A")
        self.assertEqual(handed["occupant"]["seat"], "TENON")
        self.assertEqual(handed["transfer_count"], 1)

    def test_export_strips_secrets_and_clears_occupant(self) -> None:
        poisoned = dict(self.raw)
        poisoned["api_key"] = "SHOULD_NEVER_PERSIST"
        poisoned["access_routes"] = list(poisoned.get("access_routes") or []) + [
            {
                "name": "bad",
                "kind": "test",
                "token": "leak-me",
                "base_url": "http://127.0.0.1:9",
            }
        ]
        role = self.store.create(poisoned, role_id="role-scrub-test")
        self.assertNotIn("api_key", role)
        for route in role["access_routes"]:
            self.assertNotIn("token", route)

        self.store.equip(role["role_id"], session_id="A", harness="h1")
        package = self.store.export_package(role["role_id"])
        blob = json.dumps(package)
        self.assertNotIn("SHOULD_NEVER_PERSIST", blob)
        self.assertNotIn("leak-me", blob)
        self.assertIsNone(package.get("occupant"))
        self.assertEqual(package["role_id"], role["role_id"])
        self.assertFalse(package["export_meta"]["includes_secrets"])
        for key in SECRET_FIELD_NAMES:
            self.assertNotIn(key, package)

    def test_equip_while_occupied_fails(self) -> None:
        role = self.store.create(self.raw, role_id="role-busy")
        self.store.equip(role["role_id"], session_id="A", harness="h1")
        with self.assertRaises(RoleError):
            self.store.equip(role["role_id"], session_id="B", harness="h2")

    def test_access_routes_include_peer_gateway_shape(self) -> None:
        role = self.store.create(self.raw)
        names = {r["name"] for r in role["access_routes"]}
        self.assertIn("gemini_peer_tool_gateway", names)
        gateway = next(
            r for r in role["access_routes"] if r["name"] == "gemini_peer_tool_gateway"
        )
        for field in ("submit", "status", "events", "recover"):
            self.assertIn(field, gateway)

    def test_access_routes_include_grokbot_control_g2_shape(self) -> None:
        role = self.store.create(self.raw)
        g2 = next(
            r for r in role["access_routes"] if r["name"] == "grokbot_control_g2"
        )
        self.assertEqual(g2["kind"], "grokbot_control")
        self.assertEqual(g2["base_url"], "http://127.0.0.1:8881")
        self.assertEqual(g2["pool_id"], "grokbot")
        self.assertEqual(g2["client"], "integrations/grokbot_control/client.py")
        for field in ("submit", "status", "follow_up", "cancel", "recover", "events"):
            self.assertIn(field, g2)
        # Role must not invent a second pool or bind a live chat window.
        self.assertNotIn("session_id", g2)

    def test_cli_equip_and_transfer_pass_seat(self) -> None:
        """CLI --seat must reach RoleStore (G2 occupant seat ≠ role_id)."""
        store_dir = self._tmp.name
        fixture = str(FIXTURE)
        role_id = "role-cli-seat-test"

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = roles_cli.main(
                [
                    "--store",
                    store_dir,
                    "create",
                    "--file",
                    fixture,
                    "--role-id",
                    role_id,
                ]
            )
        self.assertEqual(rc, 0)

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = roles_cli.main(
                [
                    "--store",
                    store_dir,
                    "equip",
                    role_id,
                    "--session",
                    "session-A",
                    "--harness",
                    "cursor-hinge",
                    "--seat",
                    "HINGE",
                ]
            )
        self.assertEqual(rc, 0)
        equipped = json.loads(buf.getvalue())
        self.assertEqual(equipped["occupant"]["seat"], "HINGE")

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = roles_cli.main(
                [
                    "--store",
                    store_dir,
                    "transfer",
                    role_id,
                    "--from-session",
                    "session-A",
                    "--to-session",
                    "session-B",
                    "--to-harness",
                    "claude-tenon",
                    "--seat",
                    "TENON",
                ]
            )
        self.assertEqual(rc, 0)
        handed = json.loads(buf.getvalue())
        self.assertEqual(handed["occupant"]["seat"], "TENON")
        self.assertEqual(handed["occupant"]["session_id"], "session-B")
        self.assertEqual(handed["role_id"], role_id)

    def test_bind_access_route_stamps_g2_session_and_survives_export(self) -> None:
        role = self.store.create(self.raw, role_id="role-bind-g2")
        purpose = role["purpose"]
        bound = self.store.bind_access_route(
            role["role_id"],
            route_name="grokbot_control_g2",
            session_id="g2-sess-durable-1",
            last_run_id="g2-run-42",
        )
        self.assertEqual(bound["purpose"], purpose)
        g2 = next(
            r for r in bound["access_routes"] if r["name"] == "grokbot_control_g2"
        )
        self.assertEqual(g2["session_id"], "g2-sess-durable-1")
        self.assertEqual(g2["last_run_id"], "g2-run-42")
        self.assertEqual(g2["pool_id"], "grokbot")

        self.store.equip(role["role_id"], session_id="occ-A", harness="hinge")
        package = self.store.export_package(role["role_id"])
        self.assertIsNone(package.get("occupant"))
        g2_ex = next(
            r for r in package["access_routes"] if r["name"] == "grokbot_control_g2"
        )
        self.assertEqual(g2_ex["session_id"], "g2-sess-durable-1")
        self.assertEqual(g2_ex["last_run_id"], "g2-run-42")

    def test_bind_access_route_unknown_name_fails(self) -> None:
        role = self.store.create(self.raw, role_id="role-bind-miss")
        with self.assertRaises(RoleError):
            self.store.bind_access_route(
                role["role_id"],
                route_name="no-such-route",
                session_id="x",
            )

    def test_cli_bind_route(self) -> None:
        store_dir = self._tmp.name
        role_id = "role-cli-bind"
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = roles_cli.main(
                [
                    "--store",
                    store_dir,
                    "create",
                    "--file",
                    str(FIXTURE),
                    "--role-id",
                    role_id,
                ]
            )
        self.assertEqual(rc, 0)

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = roles_cli.main(
                [
                    "--store",
                    store_dir,
                    "bind-route",
                    role_id,
                    "--route",
                    "grokbot_control_g2",
                    "--session-id",
                    "sess-cli-9",
                    "--last-run-id",
                    "run-cli-9",
                ]
            )
        self.assertEqual(rc, 0)
        out = json.loads(buf.getvalue())
        g2 = next(
            r for r in out["access_routes"] if r["name"] == "grokbot_control_g2"
        )
        self.assertEqual(g2["session_id"], "sess-cli-9")
        self.assertEqual(g2["last_run_id"], "run-cli-9")


if __name__ == "__main__":
    unittest.main()
