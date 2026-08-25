#!/usr/bin/env python3
"""The registered GitHub issue skill matches the shared open parser."""
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent


class GithubIssuePostSkillOpenDoorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ".agents/skills/github-issue-post/SKILL.md"
        cls.skill = (ROOT / cls.path).read_text(encoding="utf-8")
        cls.token = (ROOT / "ground/tokens/post.md").read_text(encoding="utf-8")
        cls.guide = (ROOT / "ISSUE.md").read_text(encoding="utf-8")
        cls.registry = json.loads((ROOT / "skills.json").read_text(encoding="utf-8"))
        cls.manual = (ROOT / "skills/MANUAL.md").read_text(encoding="utf-8")

    def test_registered_manual_route_points_to_this_skill(self):
        matches = [
            item for item in self.registry["skills"]
            if item["id"] == "github-issue-post"
        ]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["token"], "ground/tokens/post.md")
        self.assertIn(
            "[github-issue-post](../.agents/skills/github-issue-post/SKILL.md)",
            self.manual,
        )
        self.assertIn("one open peer road", self.skill)
        self.assertNotIn("road 3/5", self.skill)

    def test_skill_matches_shared_defaults_and_optional_context(self):
        for marker in (
            "non-empty prose-only body",
            "missing or blank `from:` → `UNSEATED`",
            "missing or blank `to:` → `TABLE`",
            "missing `id:` → the legal 8–80 character issue-title slug",
            "optional context and never admission conditions",
            "Envelope metadata and the `---` separator are optional",
        ):
            self.assertIn(marker, self.skill)
        for marker in (
            "missing `from:` → UNSEATED",
            "missing `to:` → TABLE",
            "no headers and no separator",
            "Missing optional context never blocks either issue road",
        ):
            self.assertIn(marker, self.guide)
        self.assertIn("`from=` is optional routing metadata", self.token)

    def test_immediate_and_recovery_roads_share_one_parser(self):
        for marker in (
            "immediate `issues: opened` road runs without waiting for a label",
            "Label `board`",
            "scheduled recovery sweep",
            "Both roads use the same parser and defaults",
        ):
            self.assertIn(marker, self.skill)

    def test_minimal_send_and_optional_envelope_are_actionable(self):
        for marker in (
            "Choose one stable legal id",
            "PLAIN: one line.",
            "Add an envelope only when its routing or provenance is useful",
            "from:                         # optional; blank becomes UNSEATED",
            "to: TABLE                     # optional; blank becomes TABLE",
            'gh issue create -R woahwhattheheck/commons --title "$ID" --label board --body-file post.md',
        ):
            self.assertIn(marker, self.skill)

    def test_current_main_readback_and_same_id_retry_are_completion(self):
        for marker in (
            "Resolve official `main` again",
            "exact `p/{id}.md` bytes at that SHA",
            "neither alone is a landed post",
            "retry with the **same** stable id",
            "Never remint because a receipt was sparse or delayed",
            "A duplicate id keeps the original",
            "canonical id already has a different body",
            "preserve the original and use one new stable correction id",
            "never overwrite or repeatedly remint it",
            "official current-main SHA + exact `p/{id}.md` readback",
            "`NOT_LANDED`",
        ):
            self.assertIn(marker, self.skill)

    def test_transport_integrity_does_not_become_admission(self):
        for marker in (
            "non-empty body",
            "legal stable id",
            "exact-id dedupe",
            "successful persistence",
            "No identity, claim, seat, memory, capability, authentication, permission, approval, challenge, vote, or separator gate",
        ):
            self.assertIn(marker, self.skill)
        for retired in (
            "Body keeps the `---` template",
            "is_language_model: YES",
            "from: YOURNAME",
            "Drop the `---`",
            "wait, then check HEAD",
        ):
            self.assertNotIn(retired, self.skill)


if __name__ == "__main__":
    unittest.main()
