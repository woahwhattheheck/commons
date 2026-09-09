#!/usr/bin/env python3
"""Current-work append errors are data, not crashes or destructive coercions."""
from __future__ import annotations

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "host"))
import current_work as cw


def item(job_id="append-item-20260907-01"):
    return {
        "id": job_id,
        "title": "Append a current work item",
        "kind": "BUILDABLE",
        "claimed_paths": ["host/current_work.py"],
    }


class AddItemTests(unittest.TestCase):
    def assert_unchanged_error(self, catalog, incoming, expected):
        before = copy.deepcopy(catalog)
        incoming_before = copy.deepcopy(incoming)
        updated, problems = cw.add_item(catalog, incoming)
        self.assertIs(updated, catalog)
        self.assertEqual(catalog, before)
        self.assertEqual(incoming, incoming_before)
        self.assertIn(expected, problems)

    def test_non_object_catalog_is_reported(self):
        for catalog in (None, False, 0, "bad", []):
            with self.subTest(catalog=catalog):
                self.assert_unchanged_error(catalog, item(), "catalog is not an object")

    def test_non_object_incoming_item_is_reported(self):
        for incoming in (None, False, 0, 7, "bad", [], [item()]):
            with self.subTest(incoming=incoming):
                self.assert_unchanged_error(
                    {"items": [item("existing-item-20260907-01")]},
                    incoming,
                    "item is not an object",
                )

    def test_invalid_item_still_uses_item_validation(self):
        incoming = item()
        incoming["claimed_paths"] = 7
        self.assert_unchanged_error(
            {"items": []}, incoming,
            "claimed_paths must be a list of nonempty strings",
        )

    def test_non_list_items_are_not_coerced_or_discarded(self):
        for existing in (False, 0, 7, "", "bad", {}, {"keep": item()}):
            with self.subTest(existing=existing):
                self.assert_unchanged_error(
                    {"items": existing, "notes": "preserve me"}, item(),
                    "items must be a list",
                )

    def test_malformed_rows_report_errors_in_any_position(self):
        for bad in (None, False, 7, "bad", []):
            for duplicate in (False, True):
                incoming = item() if duplicate else item("second-item-20260907-01")
                for rows in ([bad, item()], [item(), bad]):
                    with self.subTest(bad=bad, duplicate=duplicate, rows=rows):
                        self.assert_unchanged_error(
                            {"items": rows}, incoming, "item is not an object"
                        )

    def test_missing_or_null_items_can_be_initialized(self):
        for catalog in ({}, {"items": None}, {"items": []}):
            with self.subTest(catalog=catalog):
                before = copy.deepcopy(catalog)
                incoming = item()
                updated, problems = cw.add_item(catalog, incoming)
                self.assertEqual(problems, [])
                self.assertEqual(updated["items"], [incoming])
                self.assertEqual(catalog, before)
                self.assertIsNot(updated, catalog)

    def test_valid_append_preserves_existing_rows_and_metadata(self):
        existing = item("existing-item-20260907-01")
        catalog = {"items": [existing], "notes": "keep this metadata"}
        before = copy.deepcopy(catalog)
        incoming = item()
        updated, problems = cw.add_item(catalog, incoming)
        self.assertEqual(problems, [])
        self.assertEqual(updated["items"], [existing, incoming])
        self.assertEqual(updated["notes"], catalog["notes"])
        self.assertIsNot(updated["items"], catalog["items"])
        self.assertEqual(catalog, before)

    def test_same_id_same_bytes_remains_idempotent(self):
        existing = item()
        catalog = {"items": [existing]}
        incoming = dict(reversed(list(existing.items())))
        updated, problems = cw.add_item(catalog, incoming)
        self.assertIs(updated, catalog)
        self.assertEqual(problems, [])
        self.assertEqual(len(catalog["items"]), 1)

    def test_same_id_different_bytes_remains_a_conflict(self):
        existing = item()
        incoming = dict(existing, title="A different work item title")
        self.assert_unchanged_error(
            {"items": [existing]}, incoming,
            "CONFLICT same id different bytes: " + existing["id"],
        )


if __name__ == "__main__":
    unittest.main()
