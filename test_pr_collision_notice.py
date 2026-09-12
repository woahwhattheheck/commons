#!/usr/bin/env python3

import email.message
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pr_collision_notice as notice


def _headers(values: dict[str, str]) -> email.message.Message:
    message = email.message.Message()
    for key, value in values.items():
        message[key] = value
    return message


def _http_error(code: int, body: str, headers: dict[str, str] | None = None) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://api.github.com/repos/woahwhattheheck/commons/pulls/12212/files?per_page=100&page=1",
        code,
        "Forbidden" if code == 403 else "Too Many Requests",
        _headers(headers or {}),
        io.BytesIO(body.encode("utf-8")),
    )


class FakeAPI:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.comments: list[dict] = []

    def list_open_pulls_with_files(self, repository: str):
        self.calls.append(("batch", repository))
        return (
            [
                {"number": 10, "html_url": "https://example.test/10", "title": "self"},
                {"number": 12, "html_url": "https://example.test/12", "title": "peer"},
            ],
            {
                10: [{"filename": "shared.json"}],
                12: [{"filename": "shared.json"}],
            },
        )

    def paged(self, path: str):
        self.calls.append(("paged", path))
        if path.endswith("/comments"):
            return list(self.comments)
        raise AssertionError(f"unexpected REST fan-out {path}")

    def request(self, method: str, path: str, payload=None):
        self.calls.append((method, path))
        return {"id": 1}


class CollisionNoticeTests(unittest.TestCase):
    def test_workflow_is_event_only_and_never_executes_pr_head(self) -> None:
        workflow = (Path(__file__).parent / ".github" / "workflows" / "pr-collision-notice.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("pull_request_target:", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertIn("ref: ${{ github.event.repository.default_branch }}", workflow)
        self.assertIn("ref: ${{ github.event.pull_request.base.sha }}", workflow)
        self.assertIn("python3 listener/pr_collision_notice.py", workflow)
        self.assertNotIn("github.event.pull_request.head.sha", workflow)
        self.assertIn("pull-requests: write", workflow)
        self.assertNotIn("contents: write", workflow)

    def test_workflow_runs_default_branch_listener_not_stale_base_script(self) -> None:
        workflow = (Path(__file__).parent / ".github" / "workflows" / "pr-collision-notice.yml").read_text(
            encoding="utf-8"
        )
        listener_index = workflow.index("ref: ${{ github.event.repository.default_branch }}")
        wake_index = workflow.index("ref: ${{ github.event.pull_request.base.sha }}")
        run_index = workflow.index("python3 listener/pr_collision_notice.py")
        self.assertLess(listener_index, wake_index)
        self.assertLess(wake_index, run_index)
        self.assertIn("path: listener", workflow)
        self.assertNotIn("run: python3 pr_collision_notice.py", workflow)

    def test_exact_open_pr_overlap_is_advisory(self) -> None:
        rows = notice.find_pr_overlaps(
            10,
            {"alpha.py", "shared.json"},
            [
                {"number": 10, "html_url": "self", "title": "self"},
                {"number": 12, "html_url": "https://example.test/12", "title": "peer"},
                {"number": 11, "html_url": "https://example.test/11", "title": "disjoint"},
            ],
            {
                11: [{"filename": "other.py"}],
                12: [{"filename": "shared.json"}, {"filename": "third.py"}],
            },
        )
        self.assertEqual(rows, [{
            "number": 12,
            "url": "https://example.test/12",
            "title": "peer",
            "paths": ["shared.json"],
        }])
        body = notice.render_notice(10, "abc123", rows, [])
        self.assertIn("Advisory only", body)
        self.assertIn("[#12](https://example.test/12): `shared.json`", body)
        self.assertNotIn("block", body.lower().replace("never blocks", ""))

    def test_active_wake_job_literal_path_mentions_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "active.json").write_text(json.dumps({
                "job_id": "active",
                "status": "OPEN",
                "task": "touch src/shared.py and docs/elsewhere.md",
            }), encoding="utf-8")
            (root / "done.json").write_text(json.dumps({
                "job_id": "done",
                "status": "COMPLETE",
                "task": "touch src/shared.py",
            }), encoding="utf-8")
            (root / "broken.json").write_text("{", encoding="utf-8")
            rows = notice.find_wake_job_overlaps(root, {"src/shared.py", "other.py"})
        self.assertEqual(rows, [{"job_id": "active", "status": "OPEN", "paths": ["src/shared.py"]}])

    def test_clear_notice_is_stable_and_explicit(self) -> None:
        body = notice.render_notice(42, "deadbeef", [], [])
        self.assertTrue(body.startswith(notice.MARKER))
        self.assertIn("No exact path overlaps detected.", body)
        self.assertIn("never gates, closes, labels, or delays", body)

    def test_installation_rate_limit_retries_then_reads_files(self) -> None:
        sleeps: list[float] = []
        bodies = [
            _http_error(
                403,
                '{"message":"API rate limit exceeded for installation."}',
                {"Retry-After": "7", "X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "7"},
            ),
            io.BytesIO(json.dumps([{"filename": "shared.json"}]).encode("utf-8")),
        ]

        def fake_urlopen(request, timeout=30):
            body = bodies.pop(0)
            if isinstance(body, urllib.error.HTTPError):
                raise body
            return body

        api = notice.GitHubAPI("token", sleeper=sleeps.append, clock=lambda: 0.0, max_retries=3)
        with patch("pr_collision_notice.urllib.request.urlopen", side_effect=fake_urlopen):
            rows = api.paged("/repos/woahwhattheheck/commons/pulls/12212/files")
        self.assertEqual(rows, [{"filename": "shared.json"}])
        self.assertEqual(sleeps, [7.0])
        self.assertEqual(bodies, [])

    def test_non_rate_limit_403_fails_closed_without_sleep(self) -> None:
        sleeps: list[float] = []

        def fake_urlopen(request, timeout=30):
            raise _http_error(403, '{"message":"Resource not accessible by integration"}')

        api = notice.GitHubAPI("token", sleeper=sleeps.append, clock=lambda: 0.0, max_retries=3)
        with patch("pr_collision_notice.urllib.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaisesRegex(RuntimeError, "Resource not accessible"):
                api.request("GET", "/repos/woahwhattheheck/commons/pulls/12212/files")
        self.assertEqual(sleeps, [])

    def test_rate_limit_retries_exhausted_still_fail_closed(self) -> None:
        sleeps: list[float] = []

        def fake_urlopen(request, timeout=30):
            raise _http_error(
                403,
                '{"message":"API rate limit exceeded for installation."}',
                {"Retry-After": "3"},
            )

        api = notice.GitHubAPI("token", sleeper=sleeps.append, clock=lambda: 0.0, max_retries=2)
        with patch("pr_collision_notice.urllib.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaisesRegex(RuntimeError, "rate limit exceeded for installation"):
                api.request("GET", "/repos/woahwhattheheck/commons/pulls/12212/files")
        self.assertEqual(sleeps, [3.0, 3.0])

    def test_run_uses_batched_open_pr_files_not_per_pr_rest_fanout(self) -> None:
        api = FakeAPI()
        with tempfile.TemporaryDirectory() as tmp:
            event_path = Path(tmp) / "event.json"
            event_path.write_text(json.dumps({
                "pull_request": {"number": 10, "head": {"sha": "abc123"}},
                "repository": {"full_name": "woahwhattheheck/commons"},
            }), encoding="utf-8")
            result = notice.run(event_path, Path(tmp), api)  # type: ignore[arg-type]
        self.assertEqual(result, "created collision notice")
        self.assertEqual(api.calls[0], ("batch", "woahwhattheheck/commons"))
        self.assertEqual(api.calls[1], ("paged", "/repos/woahwhattheheck/commons/issues/10/comments"))
        self.assertEqual(api.calls[2], ("POST", "/repos/woahwhattheheck/commons/issues/10/comments"))
        self.assertFalse(any(path.startswith("/repos/") and "/pulls/" in path and path.endswith("/files") for _, path in api.calls))

    def test_graphql_batches_open_pr_files_and_falls_back_for_truncated_files(self) -> None:
        graphql_payload = {
            "data": {
                "repository": {
                    "pullRequests": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {
                                "number": 10,
                                "url": "https://example.test/10",
                                "title": "self",
                                "files": {
                                    "pageInfo": {"hasNextPage": False},
                                    "nodes": [{"path": "shared.json"}],
                                },
                            },
                            {
                                "number": 12,
                                "url": "https://example.test/12",
                                "title": "peer",
                                "files": {
                                    "pageInfo": {"hasNextPage": True},
                                    "nodes": [{"path": "shared.json"}],
                                },
                            },
                        ],
                    }
                }
            }
        }
        rest_files = [{"filename": "shared.json"}, {"filename": "extra.py"}]
        payloads = [graphql_payload, rest_files]

        def fake_urlopen(request, timeout=30):
            body = payloads.pop(0)
            return io.BytesIO(json.dumps(body).encode("utf-8"))

        api = notice.GitHubAPI("token", sleeper=lambda _delay: None, clock=lambda: 0.0)
        with patch("pr_collision_notice.urllib.request.urlopen", side_effect=fake_urlopen):
            pulls, files_by_pr = api.list_open_pulls_with_files("woahwhattheheck/commons")
        self.assertEqual([row["number"] for row in pulls], [10, 12])
        self.assertEqual(files_by_pr[10], [{"filename": "shared.json"}])
        self.assertEqual(files_by_pr[12], rest_files)
        self.assertEqual(payloads, [])

    def test_graphql_error_falls_back_to_rest_listing(self) -> None:
        graphql_error = {"errors": [{"message": "Field 'files' doesn't exist"}]}
        open_prs = [{"number": 10, "html_url": "https://example.test/10", "title": "self"}]
        files = [{"filename": "shared.json"}]
        payloads = [graphql_error, open_prs, files]

        def fake_urlopen(request, timeout=30):
            return io.BytesIO(json.dumps(payloads.pop(0)).encode("utf-8"))

        api = notice.GitHubAPI("token", sleeper=lambda _delay: None, clock=lambda: 0.0)
        with patch("pr_collision_notice.urllib.request.urlopen", side_effect=fake_urlopen):
            pulls, files_by_pr = api.list_open_pulls_with_files("woahwhattheheck/commons")
        self.assertEqual(pulls, open_prs)
        self.assertEqual(files_by_pr[10], files)
        self.assertEqual(payloads, [])


if __name__ == "__main__":
    unittest.main()
