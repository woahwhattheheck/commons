#!/usr/bin/env python3
"""The DIRECTIVES worker routes work without recreating an approval tier."""
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent


class TakeALineOpenDoorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (ROOT / ".agents/skills/take-a-line/SKILL.md").read_text(encoding="utf-8")
        cls.token = (ROOT / "ground/tokens/directives.md").read_text(encoding="utf-8")
        cls.grants = (ROOT / "GRANTS.md").read_text(encoding="utf-8")
        cls.registry = json.loads((ROOT / "skills.json").read_text(encoding="utf-8"))

    def test_registry_routes_directives_work_here(self):
        matches = [item for item in self.registry["skills"] if item["id"] == "take-a-line"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["token"], "ground/tokens/directives.md")

    def test_grants_are_evidence_not_permission(self):
        self.assertIn("Owner evidence: `GRANTS.md`", self.skill)
        for source in (self.skill, self.token, self.grants):
            self.assertIn("not a permission registry", source)
        self.assertIn("historical owner words and receipts", self.token)

    def test_owner_instruction_executes_without_court_or_approval_wait(self):
        for marker in (
            "Direct owner instructions execute",
            "without waiting for permission, approval, Court, a bench, or a session",
            "never use that search to decide who may work",
            "Court discussion, if any, stays advisory",
        ):
            self.assertIn(marker, self.token)
        self.assertIn("A current owner instruction is already work scope", self.skill)
        self.assertIn("never to decide who may build", self.skill)

    def test_current_main_overlap_and_full_receipt_contract_remain(self):
        for marker in (
            "Read the **current** `DIRECTIVES.md` on live HEAD",
            "active peer claims for the exact target paths",
            "subtract that overlap and take the smallest compatible remainder",
            "Build. Land. Post a receipt with a new id",
            "A commit + a `p/{id}.md` + a `DIRECTIVES.md` status sentence that names the receipt command",
        ):
            self.assertIn(marker, self.skill)
        for marker in (
            "Take a line. Build it. Land it.",
            "active exact-path peer claims",
            "subtract that overlap and build the smallest compatible remainder",
            "coordination describes file ownership, not permission to work",
            "Do not remint a landed id",
        ):
            self.assertIn(marker, self.token)

    def test_retired_permission_question_stays_absent(self):
        active = "\n".join((self.skill, self.token))
        for retired in (
            "Permission: `GRANTS.md`",
            "Would Bryce approve?",
            "court cannot deny",
        ):
            self.assertNotIn(retired, active)


if __name__ == "__main__":
    unittest.main()
