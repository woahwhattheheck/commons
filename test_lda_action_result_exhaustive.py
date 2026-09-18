#!/usr/bin/env python3
"""Keep the LDA action-result contract compile-exhaustive."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACTION_SERVICE = (
    ROOT
    / "lda"
    / "app"
    / "src"
    / "main"
    / "java"
    / "com"
    / "local"
    / "deviceagent"
    / "ActionAccessibilityService.kt"
)
ORCHESTRATOR = (
    ROOT
    / "lda"
    / "app"
    / "src"
    / "main"
    / "java"
    / "com"
    / "local"
    / "deviceagent"
    / "AgentOrchestrator.kt"
)


class TestLdaActionResultExhaustive(unittest.TestCase):
    def test_orchestrator_handles_every_action_result(self):
        action_source = ACTION_SERVICE.read_text(encoding="utf-8")
        orchestrator_source = ORCHESTRATOR.read_text(encoding="utf-8")

        enum_match = re.search(
            r"enum\s+class\s+ActionResult\s*\{([^}]*)\}",
            action_source,
        )
        self.assertIsNotNone(enum_match, "ActionResult enum must remain discoverable")

        enum_members = {
            item.strip()
            for item in enum_match.group(1).split(",")
            if item.strip()
        }
        handled_members = set(
            re.findall(r"ActionResult\.([A-Z_]+)\s*->", orchestrator_source)
        )

        self.assertNotIn(
            "NEEDS_CONFIRM",
            enum_members,
            "the open executor must not regain an app-layer confirmation state",
        )
        self.assertEqual(enum_members, handled_members)


if __name__ == "__main__":
    unittest.main()
