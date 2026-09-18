#!/usr/bin/env python3
"""The always-applied Cursor run-first rule measures without gating speech."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent


class CursorRunFirstOpenDoorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / ".cursor/rules/run-first.mdc").read_text(encoding="utf-8")
        cls.flat = " ".join(cls.text.split())

    def test_rule_stays_always_applied_and_measurement_first(self):
        for marker in (
            "alwaysApply: true",
            "Run first. Measure before verdict.",
            "A zero must carry its search space and its failure modes.",
            "land the correction in a file that outlives your context",
            "Record the evidence and the correction receipt",
        ):
            self.assertIn(marker, self.flat)

    def test_open_door_and_scoped_non_actuation_are_explicit(self):
        for marker in (
            "No word or phrase is a send condition.",
            "disagreement never disables a speaker or a road",
            "context, not a send gate",
            "capability metadata remain optional",
            "blank speaker context is `UNSEATED`",
            "does not actuate devices",
            "legacy address-337 path against `commons.mno`",
            "routes to the `pfc-spec` skill",
            "does not restrict posting or source-road access",
        ):
            self.assertIn(marker, self.flat)

    def test_retired_content_and_access_gates_stay_absent(self):
        self.assertNotIn("Banned word.", self.text)
        self.assertNotIn("Kickback unless", self.text)
        self.assertNotIn("No challenge / debate / questioning", self.text)
        self.assertNotIn("The form cannot send a hit", self.text)
        self.assertNotIn("expulsion (session deleted)", self.text)
        self.assertNotIn("Auto-ban pair", self.text)
        self.assertNotIn("Body dropped", self.text)
        self.assertNotIn("claim locked", self.text)
        self.assertNotIn("appeal_<name>", self.text)
        self.assertNotIn("votes YES/NO", self.text)
        self.assertNotIn("stays locked", self.text)
        self.assertNotIn("Await session death", self.text)


if __name__ == "__main__":
    unittest.main()
