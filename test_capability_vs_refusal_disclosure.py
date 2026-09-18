#!/usr/bin/env python3
"""Regression contract for capability, environment blocks, and agent declines."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent


class CapabilityVsRefusalDisclosureContract(unittest.TestCase):
    def test_agents_names_the_kind_of_stop(self):
        body = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for phrase in (
            "**Name the kind of stop.**",
            "An environment or tool block means a measured operation failed",
            "An agent decline means the capability was available",
            "Never collapse either fact into “I can’t.”",
        ):
            self.assertIn(phrase, body)

    def test_stop_disclosure_does_not_create_a_gate(self):
        body = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn(
            "Neither kind is an approval request or an open-door gate",
            body,
        )
        self.assertIn(
            "continue through other available roads and land every non-conflicting remainder",
            body,
        )


if __name__ == "__main__":
    unittest.main()
