#!/usr/bin/env python3

import json
import tempfile
import unittest
from pathlib import Path

import merged_branch_janitor as janitor


def event(*, merged=True, head_repo="woahwhattheheck/commons", head_ref="feature"):
    return {
        "repository": {
            "full_name": "woahwhattheheck/commons",
            "default_branch": "main",
        },
        "pull_request": {
            "merged": merged,
            "head": {"ref": head_ref, "repo": {"full_name": head_repo}},
            "base": {"ref": "main", "repo": {"full_name": "woahwhattheheck/commons"}},
        },
    }


class FakeAPI:
    def __init__(self):
        self.deleted = []

    def delete_ref(self, repository, branch):
        self.deleted.append((repository, branch))


class MergedBranchJanitorTests(unittest.TestCase):
    def test_workflow_is_event_only_and_uses_trusted_base(self):
        workflow = (Path(__file__).parent / ".github" / "workflows" / "merged-branch-janitor.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("pull_request_target:", workflow)
        self.assertIn("types: [closed]", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertIn("ref: ${{ github.event.pull_request.base.sha }}", workflow)
        self.assertNotIn("github.event.pull_request.head.sha", workflow)
        self.assertIn("contents: write", workflow)

    def test_eligible_same_repository_branch(self):
        self.assertEqual(
            janitor.branch_to_delete(event(head_ref="codex/finished-lane")),
            ("woahwhattheheck/commons", "codex/finished-lane"),
        )

    def test_skips_forks_unmerged_and_protected_branches(self):
        self.assertIsNone(janitor.branch_to_delete(event(merged=False)))
        self.assertIsNone(janitor.branch_to_delete(event(head_repo="peer/fork")))
        self.assertIsNone(janitor.branch_to_delete(event(head_ref="main")))

    def test_run_deletes_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "event.json"
            path.write_text(json.dumps(event(head_ref="feature/x")), encoding="utf-8")
            api = FakeAPI()
            result = janitor.run(path, api)
        self.assertEqual(api.deleted, [("woahwhattheheck/commons", "feature/x")])
        self.assertIn("deleted merged branch", result)


if __name__ == "__main__":
    unittest.main()
