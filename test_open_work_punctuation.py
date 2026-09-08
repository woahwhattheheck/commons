#!/usr/bin/env python3
"""Regression coverage for prose-final periods in open-work markers."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))
import open_work as ow  # noqa: E402


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def commit_tree(root):
    subprocess.check_call(["git", "init", "-q"], cwd=root)
    subprocess.check_call(["git", "add", "."], cwd=root)
    subprocess.check_call(
        ["git", "-c", "user.name=Open Work Test",
         "-c", "user.email=open-work@example.invalid",
         "commit", "-qm", "fixture"], cwd=root,
    )
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()


class MarkerPunctuationTests(unittest.TestCase):
    def test_unquoted_sentence_period_is_not_part_of_id(self):
        self.assertEqual(
            ow.extract_work_ids(
                "WORK ORDER live-feed-stale-fresh-order-20260830-01. Completed."
            ),
            ["live-feed-stale-fresh-order-20260830-01"],
        )

    def test_owner_marker_and_ellipsis_are_canonical(self):
        self.assertEqual(
            ow.extract_work_ids(
                "OWNER LAND ORDER open-door-main-push-report-20260830-01... next"
            ),
            ["open-door-main-push-report-20260830-01"],
        )

    def test_internal_period_is_preserved(self):
        self.assertEqual(
            ow.extract_work_ids("WORK ORDER namespace.v2-work-20260830-01"),
            ["namespace.v2-work-20260830-01"],
        )

    def test_backtick_delimited_terminal_period_is_literal(self):
        self.assertEqual(
            ow.extract_work_ids("WORK ORDER `literal-terminal-dot-20260830-01.`"),
            ["literal-terminal-dot-20260830-01."],
        )

    def test_header_id_is_not_normalized(self):
        parsed = ow.parse_structured_record(
            "id: literal-header-id-20260830-01.\n\n---\n\n"
            "WORK ORDER `literal-header-id-20260830-01.`\n"
        )
        self.assertEqual(parsed["id"], "literal-header-id-20260830-01.")
        self.assertEqual(parsed["work_ids"], ["literal-header-id-20260830-01."])

    def test_project_does_not_create_dotted_phantom_rows(self):
        tmp = tempfile.mkdtemp(prefix="open-work-period-")
        try:
            live = "live-feed-stale-fresh-order-20260830-01"
            push = "open-door-main-push-report-20260830-01"
            write(
                os.path.join(tmp, "p", live + ".md"),
                "id: %s\n\n---\n\nWORK ORDER %s. Completed.\n" % (live, live),
            )
            write(
                os.path.join(tmp, "p", push + ".md"),
                "id: %s\n\n---\n\nOWNER LAND ORDER %s. Completed.\n" % (push, push),
            )
            write(
                os.path.join(tmp, "wake_jobs", "period.json"),
                json.dumps({
                    "status": "DONE",
                    "task": "WORK ORDER %s. Completed." % live,
                    "result_address": "p/%s.md" % live,
                }),
            )
            sha = commit_tree(tmp)
            snapshot = ow.project(tmp, sha)
            by_id = {row["id"]: row for row in snapshot["items"]}
            self.assertEqual(by_id[live]["class"], "LANDED")
            self.assertEqual(by_id[push]["class"], "LANDED")
            self.assertNotIn(live + ".", by_id)
            self.assertNotIn(push + ".", by_id)
            self.assertEqual(snapshot["counts"]["OPEN"], 0)
            self.assertEqual(snapshot["counts"]["DEAD_CLAIM"], 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
