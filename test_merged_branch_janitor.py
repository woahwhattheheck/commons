#!/usr/bin/env python3

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError

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


def http_error(code: int, body: str, msg: str = "Unprocessable Entity") -> HTTPError:
    return HTTPError(
        "https://api.github.com/repos/woahwhattheheck/commons/git/refs/heads/feature",
        code,
        msg,
        hdrs=None,
        fp=io.BytesIO(body.encode("utf-8")),
    )


class FakeAPI:
    def __init__(self, outcome="deleted"):
        self.deleted = []
        self.outcome = outcome

    def delete_ref(self, repository, branch):
        self.deleted.append((repository, branch))
        return self.outcome


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

    def test_422_reference_does_not_exist_is_already_absent(self):
        # Measured failure: run 33676288081 / PR 8320
        # RuntimeError: GitHub branch delete failed (422):
        # {"message":"Reference does not exist",...}
        body = (
            '{"message":"Reference does not exist",'
            '"documentation_url":"https://docs.github.com/rest/git/refs#delete-a-reference",'
            '"status":"422"}'
        )
        self.assertTrue(janitor.is_absent_ref_error(422, body))
        self.assertFalse(janitor.is_absent_ref_error(422, '{"message":"Validation Failed"}'))
        self.assertTrue(janitor.is_absent_ref_error(404, '{"message":"Not Found"}'))
        self.assertFalse(janitor.is_absent_ref_error(403, '{"message":"Resource not accessible by integration"}'))
        self.assertFalse(janitor.is_absent_ref_error(500, "internal error"))

    def test_delete_ref_treats_measured_422_as_success(self):
        body = '{"message":"Reference does not exist","status":"422"}'
        api = janitor.GitHubAPI("token")
        with mock.patch(
            "merged_branch_janitor.urllib.request.urlopen",
            side_effect=http_error(422, body),
        ):
            self.assertEqual(
                api.delete_ref("woahwhattheheck/commons", "grok-build/pr8303-terminal-20260902-01"),
                "already_absent",
            )

    def test_delete_ref_treats_404_as_already_absent(self):
        api = janitor.GitHubAPI("token")
        with mock.patch(
            "merged_branch_janitor.urllib.request.urlopen",
            side_effect=http_error(404, '{"message":"Not Found"}', msg="Not Found"),
        ):
            self.assertEqual(api.delete_ref("woahwhattheheck/commons", "feature"), "already_absent")

    def test_delete_ref_still_fails_other_422_and_5xx(self):
        api = janitor.GitHubAPI("token")
        with mock.patch(
            "merged_branch_janitor.urllib.request.urlopen",
            side_effect=http_error(422, '{"message":"Validation Failed"}'),
        ):
            with self.assertRaises(RuntimeError) as raised:
                api.delete_ref("woahwhattheheck/commons", "feature")
        self.assertIn("422", str(raised.exception))
        self.assertIn("Validation Failed", str(raised.exception))

        with mock.patch(
            "merged_branch_janitor.urllib.request.urlopen",
            side_effect=http_error(500, "boom", msg="Internal Server Error"),
        ):
            with self.assertRaises(RuntimeError) as raised:
                api.delete_ref("woahwhattheheck/commons", "feature")
        self.assertIn("500", str(raised.exception))

    def test_delete_ref_success_returns_deleted(self):
        api = janitor.GitHubAPI("token")
        with mock.patch("merged_branch_janitor.urllib.request.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value = mock.Mock()
            self.assertEqual(api.delete_ref("woahwhattheheck/commons", "feature"), "deleted")

    def test_run_reports_already_absent_without_raising(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "event.json"
            path.write_text(
                json.dumps(event(head_ref="grok-build/pr8303-terminal-20260902-01")),
                encoding="utf-8",
            )
            api = FakeAPI(outcome="already_absent")
            result = janitor.run(path, api)
        self.assertEqual(
            api.deleted,
            [("woahwhattheheck/commons", "grok-build/pr8303-terminal-20260902-01")],
        )
        self.assertEqual(
            result,
            "merged branch already absent woahwhattheheck/commons:grok-build/pr8303-terminal-20260902-01",
        )


if __name__ == "__main__":
    unittest.main()
