#!/usr/bin/env python3
"""Focused contract tests for the fail-closed tool-consumption index."""

from __future__ import annotations

import copy
import json
import unittest

from host.tool_consumption_index import (
    ToolConsumptionError,
    build_index,
    canonical_text,
    git_blob_sha,
)


SOURCE_BLOBS = {
    "skills.json": "1" * 40,
    "commands.json": "2" * 40,
    "tools.json": "3" * 40,
    "share.json": "4" * 40,
}


def fixture() -> dict[str, object]:
    return {
        "skills": {"skills": [{"id": "build"}, {"id": "review"}]},
        "commands": {"commands": [{"id": "run"}]},
        "tools": {"tools": [{"id": "meter"}, {"id": "scope"}]},
        "share": {
            "open": [
                {"id": "blank", "tool": "", "status": "OPEN"},
                {"id": "ready", "tool": "meter", "op": "life", "status": "OPEN"},
                {"id": "ghost", "tool": "missing", "status": "OPEN"},
            ],
            "done": [
                {"id": "used", "tool": "scope", "receipt": "rcpt-1", "status": "DONE"},
                {"id": "no-receipt", "tool": "meter", "receipt": "", "status": "DONE"},
                {"id": "unnamed", "tool": "", "receipt": "rcpt-2", "status": "DONE"},
            ],
            "refused": [{"id": "refused", "tool": "", "status": "REFUSED"}],
        },
    }


def build(data: dict[str, object] | None = None) -> dict[str, object]:
    data = fixture() if data is None else data
    return build_index(
        skills=data["skills"],
        commands=data["commands"],
        tools=data["tools"],
        share=data["share"],
        source_commit="a" * 40,
        source_blobs=SOURCE_BLOBS,
    )


class ToolConsumptionIndexTests(unittest.TestCase):
    def test_exact_summary_keeps_capacity_and_consumption_separate(self) -> None:
        self.assertEqual(
            build()["summary"],
            {
                "jobs_total": 7,
                "open_jobs": 3,
                "open_blank_tool": 1,
                "open_unknown_tool": 1,
                "open_allocatable": 1,
                "done_jobs": 3,
                "done_receipted_known_tool": 1,
                "refused_jobs": 1,
            },
        )

    def test_only_known_open_tool_is_allocatable(self) -> None:
        rows = build()["allocatable_open_jobs"]
        self.assertEqual([row["id"] for row in rows], ["ready"])
        self.assertEqual(rows[0]["allocation"], "ALLOCATABLE")

    def test_consumption_requires_known_tool_and_receipt(self) -> None:
        rows = build()["receipted_consumption"]
        self.assertEqual([(row["id"], row["tool"], row["receipt"]) for row in rows], [("used", "scope", "rcpt-1")])

    def test_blank_and_unknown_tools_fail_closed(self) -> None:
        rows = {row["id"]: row for row in build()["jobs"]["open"]}
        self.assertEqual(rows["blank"]["binding"], "BLANK_TOOL")
        self.assertEqual(rows["ghost"]["binding"], "UNKNOWN_TOOL")
        self.assertEqual(rows["blank"]["allocation"], "EXCLUDED")
        self.assertEqual(rows["ghost"]["allocation"], "EXCLUDED")

    def test_input_order_does_not_change_bytes(self) -> None:
        data = fixture()
        reverse = copy.deepcopy(data)
        for section in ("open", "done", "refused"):
            reverse["share"][section].reverse()
        self.assertEqual(canonical_text(build(data)), canonical_text(build(reverse)))
        json.loads(canonical_text(build(data)))

    def test_duplicate_catalog_id_fails_closed(self) -> None:
        data = fixture()
        data["tools"]["tools"].append({"id": "meter"})
        with self.assertRaisesRegex(ToolConsumptionError, "duplicate id"):
            build(data)

    def test_job_id_in_two_sections_fails_closed(self) -> None:
        data = fixture()
        data["share"]["done"].append({"id": "ready", "tool": "meter", "receipt": "r", "status": "DONE"})
        with self.assertRaisesRegex(ToolConsumptionError, "multiple sections"):
            build(data)

    def test_source_boundary_is_exact(self) -> None:
        result = build()
        self.assertEqual(result["source_blobs"], SOURCE_BLOBS)
        with self.assertRaisesRegex(ToolConsumptionError, "four source files"):
            build_index(
                skills=fixture()["skills"], commands=fixture()["commands"],
                tools=fixture()["tools"], share=fixture()["share"],
                source_commit="a" * 40, source_blobs={"share.json": "1" * 40},
            )

    def test_git_blob_sha_matches_known_empty_blob(self) -> None:
        self.assertEqual(git_blob_sha(b""), "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391")

    def test_truth_never_claims_invocation_or_job_mutation(self) -> None:
        truth = build()["truth"]
        self.assertTrue(truth["blank_or_unknown_tool_is_not_allocatable"])
        self.assertEqual(truth["jobs_mutated"], 0)
        self.assertEqual(truth["tools_invoked"], 0)


if __name__ == "__main__":
    unittest.main()
