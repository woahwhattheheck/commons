#!/usr/bin/env python3
"""The branch/PR skill coordinates work without narrowing Commons roads."""
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent


class NewBranchPrOpenRoadsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ".agents/skills/new-branch-and-pr/SKILL.md"
        cls.text = (ROOT / cls.path).read_text(encoding="utf-8")
        cls.registry = json.loads((ROOT / "skills.json").read_text(encoding="utf-8"))
        cls.manual = (ROOT / "skills/MANUAL.md").read_text(encoding="utf-8")

    def test_registered_manual_route_points_to_this_skill(self):
        matches = [item for item in self.registry["skills"] if item["id"] == "new-branch-and-pr"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["job"], "branch + PR (GitHub skill)")
        self.assertIn("[new-branch-and-pr](../.agents/skills/new-branch-and-pr/SKILL.md)", self.manual)

    def test_branch_is_fresh_non_force_optional_coordination(self):
        for marker in (
            "live** `origin/main`",
            "optional coordination, not a permission tier",
            "Run the relevant tests whether or not you added a test",
            "push without force",
            "If `main` moved",
            "re-apply the smallest compatible patch",
            "never force through a race",
        ):
            self.assertIn(marker, self.text)

    def test_all_receipt_roads_and_record_integrity_remain_open(self):
        for marker in (
            "Action Pad, form/ntfy, board issue, Slack, Commons MCP",
            "Direct Contents / Git Data",
            "current-main git",
            "open peer roads",
            "Preserve the exact id",
            "never overwrite",
            "never remint",
            "current HEAD",
        ):
            self.assertIn(marker, self.text)

    def test_high_contention_paths_coordinate_instead_of_refuse(self):
        for marker in (
            "high-contention paths",
            "re-read current HEAD",
            "coordinate exact overlap",
            "smallest tested patch",
            "not a permission tier",
        ):
            self.assertIn(marker, self.text)

    def test_output_distinguishes_candidate_from_integrated_main(self):
        for marker in (
            "Treat the PR as `CANDIDATE`",
            "review-and-ship",
            "verify the exact change on current main",
            "integrated main SHA or `NOT_LANDED`",
            "exact changed paths and coordinated overlap paths",
            "receipt id and current-HEAD readback",
        ):
            self.assertIn(marker, self.text)

    def test_retired_path_and_receipt_restrictions_stay_absent(self):
        self.assertNotIn("on any road", self.text)
        self.assertNotIn("not a direct repo write", self.text)
        self.assertNotIn("targeted tests if you added them", self.text)
        self.assertNotIn("what you refused to touch", self.text)


if __name__ == "__main__":
    unittest.main()
