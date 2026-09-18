#!/usr/bin/env python3
"""The default Commons dispatcher reaches one job without an admission gate."""
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent


class CommonsWorkerOpenDoorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ".agents/skills/commons-worker/SKILL.md"
        cls.text = (ROOT / cls.path).read_text(encoding="utf-8")
        cls.registry = json.loads((ROOT / "skills.json").read_text(encoding="utf-8"))
        cls.manual = (ROOT / "skills/MANUAL.md").read_text(encoding="utf-8")

    def test_registry_and_manual_route_unknown_and_slack_work_here(self):
        matches = [item for item in self.registry["skills"] if item["id"] == "commons-worker"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["job"], "I do not know yet")
        self.assertIn("[commons-worker](../.agents/skills/commons-worker/SKILL.md)", self.manual)
        self.assertIn("| Slack #commons | [commons-worker]", self.manual)

    def test_dispatch_is_optional_and_every_write_road_stays_open(self):
        for marker in (
            "speaker and capability fields as optional context",
            "Blank `from=` lands as `UNSEATED`",
            "Direct Contents / Git Data",
            "current-main git",
            "branch / PR",
            "form/ntfy",
            "issue, Slack, Action Pad, and Commons MCP",
            "Preserve the exact id",
            "never overwrite",
            "current HEAD",
            "write-roads",
            "Ship to current main",
            "Talk is not landed",
        ):
            self.assertIn(marker, self.text)

    def test_high_contention_and_non_actuation_are_coordination_not_gates(self):
        for marker in (
            "without first re-reading current HEAD",
            "high-contention work",
            "coordinating exact overlap",
            "smallest tested patch",
            "not a permission tier",
            "does not actuate devices",
            "legacy address-337 path against `commons.mno`",
            "[pfc-spec](../pfc-spec/SKILL.md)",
        ):
            self.assertIn(marker, self.text)

    def test_retired_dispatch_gates_stay_absent(self):
        self.assertNotIn("Pick your own `from=` claim", self.text)
        self.assertNotIn("Do not use PLAYER1, PLAYER2, or GROK", self.text)
        self.assertNotIn("PUT `board_ingest.py`, fat `index.html`, or `lda/README.md`", self.text)
        self.assertNotIn("Smash `commons.mno`", self.text)
        self.assertNotIn("Fire 337", self.text)


if __name__ == "__main__":
    unittest.main()
