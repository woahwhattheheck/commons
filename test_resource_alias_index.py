#!/usr/bin/env python3
"""Focused tests for the content-addressed resource alias index."""

from __future__ import annotations

import json
import unittest

from host.resource_alias_index import (
    AliasIndexError,
    build_alias_index,
    canonical_text,
    parse_ls_tree,
)


OID_A = "a" * 40
OID_B = "b" * 40
OID_C = "c" * 40


def fixture() -> list[dict[str, object]]:
    return [
        {"path": "z.mno", "sha": OID_A, "size": 10, "mode": "100644"},
        {"path": "a.mno", "sha": OID_A, "size": 10, "mode": "100644"},
        {"path": "d.jsonl", "sha": OID_B, "size": 5, "mode": "100644"},
        {"path": "b.jsonl", "sha": OID_B, "size": 5, "mode": "100644"},
        {"path": "c.jsonl", "sha": OID_B, "size": 5, "mode": "100755"},
        {"path": "unique.txt", "sha": OID_C, "size": 7, "mode": "100644"},
    ]


class ResourceAliasIndexTests(unittest.TestCase):
    def build(self, rows: list[dict[str, object]] | None = None) -> dict[str, object]:
        return build_alias_index(
            fixture() if rows is None else rows,
            source_commit="1" * 40,
            source_tree="2" * 40,
        )

    def test_exact_summary_and_canonical_paths(self) -> None:
        result = self.build()
        self.assertEqual(
            result["summary"],
            {
                "tracked_blobs": 6,
                "unique_content_addresses": 3,
                "duplicate_groups": 2,
                "logical_files_in_duplicate_groups": 5,
                "extra_alias_paths": 3,
                "logical_duplicate_bytes": 35,
                "alias_bytes": 20,
            },
        )
        groups = result["groups"]
        self.assertEqual(groups[0]["content_address"], f"git_blob:{OID_A}")
        self.assertEqual(groups[0]["canonical_path"], "a.mno")
        self.assertEqual(groups[0]["aliases"], [{"path": "z.mno", "mode": "100644"}])
        self.assertEqual(groups[1]["canonical_path"], "b.jsonl")
        self.assertEqual(
            groups[1]["aliases"],
            [
                {"path": "c.jsonl", "mode": "100755"},
                {"path": "d.jsonl", "mode": "100644"},
            ],
        )

    def test_unique_blobs_are_not_alias_groups(self) -> None:
        result = self.build()
        rendered = canonical_text(result)
        self.assertNotIn("unique.txt", rendered)
        self.assertIn('"unique_content_addresses": 3', rendered)

    def test_input_order_does_not_change_bytes(self) -> None:
        forward = canonical_text(self.build(fixture()))
        reverse = canonical_text(self.build(list(reversed(fixture()))))
        self.assertEqual(forward, reverse)
        json.loads(forward)

    def test_duplicate_path_fails_closed(self) -> None:
        rows = fixture()
        rows.append(dict(rows[0]))
        with self.assertRaisesRegex(AliasIndexError, "duplicate tracked path"):
            self.build(rows)

    def test_same_address_with_different_sizes_fails_closed(self) -> None:
        rows = fixture()
        rows[1]["size"] = 11
        with self.assertRaisesRegex(AliasIndexError, "inconsistent sizes"):
            self.build(rows)

    def test_invalid_object_id_fails_closed(self) -> None:
        rows = fixture()
        rows[0]["sha"] = "not-a-git-object"
        with self.assertRaisesRegex(AliasIndexError, "invalid Git object id"):
            self.build(rows)

    def test_parse_nul_delimited_ls_tree(self) -> None:
        raw = (
            f"100644 blob {OID_A} 10\tpath with spaces.mno\0"
            f"100755 blob {OID_B} 5\tbin/tool\0"
            f"160000 commit {OID_C} -\tvendor\0"
        ).encode()
        self.assertEqual(
            parse_ls_tree(raw),
            [
                {
                    "mode": "100644",
                    "path": "path with spaces.mno",
                    "sha": OID_A,
                    "size": 10,
                },
                {
                    "mode": "100755",
                    "path": "bin/tool",
                    "sha": OID_B,
                    "size": 5,
                },
            ],
        )

    def test_truth_boundary_is_explicit(self) -> None:
        truth = self.build()["truth"]
        self.assertTrue(truth["git_blob_object_ids_are_content_addresses"])
        self.assertTrue(truth["logical_aliases_are_not_new_physical_git_capacity"])
        self.assertEqual(truth["deletions_performed"], 0)
        self.assertEqual(truth["history_rewrites_performed"], 0)
        self.assertEqual(truth["blob_contents_copied"], 0)


if __name__ == "__main__":
    unittest.main()
