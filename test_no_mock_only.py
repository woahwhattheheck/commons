#!/usr/bin/env python3
"""Canary: no-mock-only law is pinned; the green test battery stays legal.

Does not assert that the word "test" is forbidden.
Does not remint durability-law or HEAD.md.
"""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
AGENTS = ROOT / "AGENTS.md"
DIRECTIVES = ROOT / "DIRECTIVES.md"
LAW = ROOT / "ground" / "NO_MOCK_ONLY.md"

OWNER_QUOTE = (
    "do not substitute a mock, test-only artifact, or minimal skeleton "
    "for the requested thing"
)
REAL_IMPL = "Build the real, usable implementation"
SCOPE = "no mock-only deliverables"
BATTERY = "green test battery"
PROVE = "Tests that prove a real implementation"


class NoMockOnlyLawTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agents = AGENTS.read_text(encoding="utf-8")
        cls.directives = DIRECTIVES.read_text(encoding="utf-8")
        cls.law = LAW.read_text(encoding="utf-8")

    def test_agents_and_directives_carry_the_no_mock_only_rule(self):
        for name, text in (
            ("AGENTS.md", self.agents),
            ("DIRECTIVES.md", self.directives),
            ("ground/NO_MOCK_ONLY.md", self.law),
        ):
            self.assertIn(OWNER_QUOTE, text, name)
            self.assertIn(REAL_IMPL, text, name)
            self.assertIn(SCOPE, text, name)
        self.assertIn("NO_MOCK_ONLY.md", self.agents)
        self.assertIn("NO_MOCK_ONLY.md", self.directives)

    def test_green_test_battery_stays_legal(self):
        for name, text in (
            ("AGENTS.md", self.agents),
            ("DIRECTIVES.md", self.directives),
            ("ground/NO_MOCK_ONLY.md", self.law),
        ):
            self.assertIn(BATTERY, text, name)
            self.assertIn(PROVE, text, name)
            self.assertIn("required, not banned", text, name)

    def test_word_test_is_not_treated_as_forbidden(self):
        # The canary itself is a test. The law files must keep "test" as a
        # legal word for the battery, not a banned token.
        for name, text in (
            ("AGENTS.md", self.agents),
            ("DIRECTIVES.md", self.directives),
        ):
            self.assertIn("test", text.lower(), name)
            self.assertNotIn("the word test is forbidden", text.lower(), name)
            self.assertNotIn("tests are forbidden", text.lower(), name)

    def test_not_an_admission_gate(self):
        for name, text in (
            ("AGENTS.md", self.agents),
            ("DIRECTIVES.md", self.directives),
            ("ground/NO_MOCK_ONLY.md", self.law),
        ):
            self.assertIn("not an admission gate", text, name)
            self.assertNotIn("login required", text.lower(), name)
            self.assertNotIn("must authenticate", text.lower(), name)

    def test_agents_pin_sits_with_execute_land_expand(self):
        expand = self.agents.index("EXPAND CAPABILITY")
        execute = self.agents.index("Do not ask if I want you to do something")
        land = self.agents.index(
            "Land unique work on current main in the same turn you build it."
        )
        pin = self.agents.index("NO MOCK-ONLY DELIVERABLES")
        self.assertLess(expand, pin)
        self.assertLess(execute, pin)
        self.assertLess(land, pin)

    def test_directives_item_67_states_scope(self):
        item = self.directives.split("### 67. No mock-only deliverables", 1)[1]
        item = item.split("\n## ", 1)[0]
        self.assertIn(SCOPE, item)
        self.assertIn(BATTERY, item)
        self.assertIn(PROVE, item)
        self.assertIn(OWNER_QUOTE, item)


if __name__ == "__main__":
    unittest.main()
