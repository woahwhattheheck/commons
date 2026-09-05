#!/usr/bin/env python3
"""Hermetic asserts for Autopsy vs Survival Proof intake page-route truth."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AUTOPSY_INTAKE = ROOT / "revenue" / "agent_failure_autopsy" / "INTAKE.md"
SURVIVAL_INTAKE = ROOT / "revenue" / "production_survival" / "INTAKE.md"


class AutopsyIntakeRunbookTests(unittest.TestCase):
    def test_autopsy_intake_exists_and_names_product(self) -> None:
        text = AUTOPSY_INTAKE.read_text(encoding="utf-8")
        self.assertTrue(AUTOPSY_INTAKE.is_file())
        self.assertIn("Agent Failure Autopsy", text)
        self.assertRegex(text, r"\$29|USD 29")
        self.assertIn("RUNBOOK.md", text)
        self.assertIn("agent-rescue.html", text)
        # Must not sell Survival Proof on the Autopsy page narrative.
        self.assertNotRegex(
            text,
            re.compile(
                r"agent-rescue\.html[^.\n]{0,120}\$2,?500",
                re.IGNORECASE,
            ),
        )
        self.assertNotIn("sells the $2,500", text)

    def test_survival_intake_does_not_sell_agent_rescue_as_2500(self) -> None:
        text = SURVIVAL_INTAKE.read_text(encoding="utf-8")
        self.assertTrue(SURVIVAL_INTAKE.is_file())
        self.assertIn("Same-Day Agent Survival Proof", text)
        self.assertIn("agent_failure_autopsy/INTAKE.md", text)
        banned = [
            "agent-rescue.html has three routes",
            "agent-rescue.html now sells the $2,500",
            "Buy button on `agent-rescue.html`",
            "Buy button on agent-rescue.html",
        ]
        for phrase in banned:
            self.assertNotIn(phrase, text, msg=f"banned stale route phrase: {phrase}")
        # Positive: explicit separation from Autopsy page.
        self.assertRegex(
            text,
            re.compile(
                r"not.*agent-rescue\.html|agent-rescue\.html.*not",
                re.IGNORECASE | re.DOTALL,
            ),
        )


if __name__ == "__main__":
    unittest.main()
