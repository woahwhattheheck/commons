#!/usr/bin/env python3

import json
import tempfile
import unittest
from pathlib import Path

import pr_collision_notice as notice


class CollisionNoticeTests(unittest.TestCase):
    def test_workflow_is_event_only_and_never_executes_pr_head(self) -> None:
        workflow = (Path(__file__).parent / ".github" / "workflows" / "pr-collision-notice.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("pull_request_target:", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertIn("ref: ${{ github.event.pull_request.base.sha }}", workflow)
        self.assertNotIn("github.event.pull_request.head.sha", workflow)
        self.assertIn("pull-requests: write", workflow)
        self.assertNotIn("contents: write", workflow)

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


if __name__ == "__main__":
    unittest.main()
