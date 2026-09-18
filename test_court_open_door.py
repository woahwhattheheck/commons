#!/usr/bin/env python3
"""Court remains a public advisory surface, never a permission tier."""
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent


class CourtOpenDoorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (ROOT / ".agents/skills/court/SKILL.md").read_text(encoding="utf-8")
        cls.token = (ROOT / "ground/tokens/court.md").read_text(encoding="utf-8")
        cls.manual = (ROOT / "skills/MANUAL.md").read_text(encoding="utf-8")
        cls.registry = json.loads((ROOT / "skills.json").read_text(encoding="utf-8"))
        cls.page = (ROOT / "court.html").read_text(encoding="utf-8")

    def test_registry_and_manual_route_court_here(self):
        matches = [item for item in self.registry["skills"] if item["id"] == "court"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["token"], "ground/tokens/court.md")
        self.assertIn("[court](../.agents/skills/court/SKILL.md)", self.manual)
        self.assertIn("A skill routes work; it is not a seat or permission tier", self.manual)

    def test_anyone_or_unseated_can_use_the_public_address(self):
        for source in (self.skill, self.token):
            for marker in (
                "`to: COURT`",
                "Anyone",
                "blank",
                "`UNSEATED`",
                "display context",
                "never identity proof, authority",
            ):
                self.assertIn(marker, source)
        self.assertIn("No content, identity, claim, seat, memory, permission, or approval gate may disable posting", self.page)
        self.assertIn("placeholder=\"optional; blank lands as UNSEATED\"", self.page)

    def test_rulings_and_sessions_are_advisory_records_not_gates(self):
        for source in (self.skill, self.token):
            for marker in (
                "`GRANT`, `DENY`, `ASSIGN_RESOURCE`",
                "advisory",
                "cannot authorize, delay, or block participation, posting, source work, reads, writes, execution",
                "not a permission registry",
                "Opening, closing, joining, or addressing",
                "presentation",
                "not a gate",
            ):
                self.assertIn(marker, source)

    def test_owner_instruction_executes_without_approval_wait(self):
        for source in (self.skill, self.token):
            for marker in (
                "Direct owner instructions",
                "execute",
                "without waiting for Court, approval, a bench, or a session banner",
                "cannot expand the operator's requested scope",
                "exact-id/current-main integrity",
            ):
                self.assertIn(marker, source)

    def test_posting_and_completion_stay_on_open_roads_and_current_main(self):
        for source in (self.skill, self.token):
            for marker in (
                "any open",
                "PLAIN line",
                "optional context",
                "exact `p/{id}.md` bytes on official current `main`",
            ):
                self.assertIn(marker, source)
            self.assertIn("never remint a landed id", source.lower())

    def test_historical_records_remain_data(self):
        for source in (self.skill, self.token):
            self.assertIn(
                "Historical bench, role, order, resource, and session records remain readable data",
                source,
            )

    def test_retired_approval_and_identity_gates_stay_absent(self):
        active = "\n".join((self.skill, self.token, self.manual))
        for retired in (
            "Would Bryce approve?",
            "court cannot deny",
            "Feature requests are pre-approved unless they violate a prior ruling",
            "ZERO/BRYCE override",
            "Do not speak as BRYCE or ZERO",
            "from= is a claim",
            "337 NO",
        ):
            self.assertNotIn(retired, active)


if __name__ == "__main__":
    unittest.main()
