#!/usr/bin/env python3
"""Hermetic tests: create → equip A → transfer B; secrets never exported."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from roles import RoleError, RoleStore, SECRET_FIELD_NAMES

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
            role_id, session_id="session-A", harness="cursor-hinge"
        )
        self.assertEqual(equipped["occupant"]["session_id"], "session-A")
        self.assertEqual(equipped["role_id"], role_id)

        handed = self.store.transfer(
            role_id,
            from_session_id="session-A",
            to_session_id="session-B",
            to_harness="claude-tenon",
        )
        self.assertEqual(handed["role_id"], role_id)
        self.assertEqual(handed["purpose"], purpose)
        self.assertEqual(
            [o["next_action"] for o in handed["obligations"]], next_actions
        )
        self.assertEqual(handed["occupant"]["session_id"], "session-B")
        self.assertEqual(handed["occupant"]["prior_session_id"], "session-A")
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


if __name__ == "__main__":
    unittest.main()
