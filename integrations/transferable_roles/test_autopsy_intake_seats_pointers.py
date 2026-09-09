#!/usr/bin/env python3
"""Hermetic: Autopsy R4 fixture points at #8901 INTAKE + #8925 SEATS."""

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
SPINE_INTAKE = "revenue/agent_failure_autopsy/INTAKE.md"
SPINE_SEATS = "revenue/agent_failure_autopsy/SEATS.md"
SPINE_SEATS_JSON = "revenue/agent_failure_autopsy/seats.json"


class AutopsyIntakeSeatsPointerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = RoleStore(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_autopsy_fixture_points_at_intake_and_seats(self) -> None:
        raw = json.loads(AUTOPSY_FIXTURE.read_text(encoding="utf-8"))
        role = self.store.create(raw)
        pointers = {k["pointer"] for k in role["knowledge"]}
        self.assertIn(SPINE_INTAKE, pointers)
        self.assertIn(SPINE_SEATS, pointers)
        self.assertIn(SPINE_SEATS_JSON, pointers)


if __name__ == "__main__":
    unittest.main()
