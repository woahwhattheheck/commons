#!/usr/bin/env python3
"""Catalogue container validation, including the real finder-zero CLI."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))
import finder_zero


class FinderCatalogShapeTests(unittest.TestCase):
    def assert_field_error(self, field, value):
        self.assertEqual(
            finder_zero.load_catalog(json.dumps({field: value})),
            {"error": "catalog %s is not an array" % field},
        )

    def test_defects_rejects_numbers(self):
        for value in (0, 1, -1, 0.0, 1.5):
            with self.subTest(value=value):
                self.assert_field_error("defects", value)

    def test_defects_rejects_booleans(self):
        for value in (False, True):
            with self.subTest(value=value):
                self.assert_field_error("defects", value)

    def test_defects_rejects_strings(self):
        for value in ("", " ", "missing", "[]"):
            with self.subTest(value=value):
                self.assert_field_error("defects", value)

    def test_defects_rejects_objects(self):
        for value in ({}, {"id": "lost-record"}):
            with self.subTest(value=value):
                self.assert_field_error("defects", value)

    def test_hands_off_rejects_numbers(self):
        for value in (0, 1, -1, 0.0, 1.5):
            with self.subTest(value=value):
                self.assert_field_error("hands_off", value)

    def test_hands_off_rejects_booleans(self):
        for value in (False, True):
            with self.subTest(value=value):
                self.assert_field_error("hands_off", value)

    def test_hands_off_rejects_strings(self):
        for value in ("", " ", "peer", "[]"):
            with self.subTest(value=value):
                self.assert_field_error("hands_off", value)

    def test_hands_off_rejects_objects(self):
        for value in ({}, {"peer": "owner"}):
            with self.subTest(value=value):
                self.assert_field_error("hands_off", value)

    def test_missing_null_and_empty_arrays_keep_existing_defaults(self):
        expected = {
            "source_id": "", "slack_ts": "", "titan": "NOT_WRITTEN",
            "defects": [], "hands_off": [],
        }
        for text in (None, "", "{}", '{"defects": null}',
                     '{"hands_off": null}',
                     '{"defects": null, "hands_off": null}',
                     '{"defects": [], "hands_off": []}'):
            with self.subTest(text=text):
                self.assertEqual(finder_zero.load_catalog(text), expected)

    def test_existing_array_item_normalization_is_unchanged(self):
        data = {
            "source_id": "  source  ", "slack_ts": " 123 ", "titan": " ",
            "defects": [None, 1, "skip", [], {}, {"id": " "},
                        {"name": " fallback ", "query": " q ", "verdict": " miss "},
                        {"id": " first ", "name": "second", "query": 42}],
            "hands_off": [None, False, 0, "", "  ", " peer ", 2, "peer"],
        }
        text = json.dumps(data)
        self.assertEqual(finder_zero.load_catalog(text), {
            "source_id": "source", "slack_ts": "123", "titan": "NOT_WRITTEN",
            "defects": [
                {"id": "fallback", "query": "q", "verdict": "MISS"},
                {"id": "first", "query": "42", "verdict": ""},
            ],
            "hands_off": ["peer", "2", "peer"],
        })
        self.assertEqual(json.loads(text), data)

    def test_current_repository_catalogue_preserves_all_rows(self):
        text = (ROOT / "ground" / "FINDER_ZERO.json").read_text(encoding="utf-8")
        source = json.loads(text)
        expected = {key: source[key] for key in ("source_id", "slack_ts", "titan", "hands_off")}
        expected["defects"] = [
            {key: item[key] for key in ("id", "query", "verdict")}
            for item in source["defects"]
        ]
        self.assertEqual(finder_zero.load_catalog(text), expected)

    def test_existing_syntax_and_top_level_errors_are_unchanged(self):
        for text in ("{", " ", "not-json"):
            with self.subTest(text=text):
                self.assertEqual(finder_zero.load_catalog(text), {"error": "catalog is not JSON"})
        for value in ([], "text", 1, 0, False, True, None):
            with self.subTest(value=value):
                self.assertEqual(finder_zero.load_catalog(json.dumps(value)),
                                 {"error": "catalog is not an object"})

    def test_error_identifies_first_malformed_field_deterministically(self):
        text = '{"hands_off": "peer", "defects": {"id": "x"}}'
        for _ in range(2):
            self.assertEqual(finder_zero.load_catalog(text),
                             {"error": "catalog defects is not an array"})

    def test_measure_tree_propagates_error_without_reading_tree(self):
        for field in ("defects", "hands_off"):
            with self.subTest(field=field):
                with patch.object(finder_zero, "_read", side_effect=AssertionError("unexpected read")), \
                     patch.object(finder_zero, "_exists", side_effect=AssertionError("unexpected stat")), \
                     patch.object(finder_zero, "measure_slack_projection", side_effect=AssertionError("unexpected projection")):
                    row = finder_zero.measure_tree("unused-root", json.dumps({field: "bad"}))
                self.assertEqual(row, {"measured": False, "error": "catalog %s is not an array" % field,
                                       "titan_write": "NOT_WRITTEN"})
                self.assertEqual(finder_zero.classify(row)["state"], "UNMEASURED")
                self.assertNotIn("find_count", row)
                self.assertNotIn("clearance", row)

    def test_cli_malformed_fields_emit_json_exit_two_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            catalog = Path(directory) / "catalog.json"
            for field, value in (("defects", 1), ("defects", "missing"),
                                 ("defects", {}), ("hands_off", True),
                                 ("hands_off", "peer"), ("hands_off", {})):
                with self.subTest(field=field, value=value):
                    catalog.write_text(json.dumps({field: value}), encoding="utf-8")
                    process = subprocess.run(
                        [sys.executable, "-B", str(ROOT / "host" / "finder_zero.py"),
                         "--root", directory, "--catalog", str(catalog)],
                        cwd=ROOT, text=True, capture_output=True, timeout=10,
                    )
                    self.assertEqual(process.returncode, 2, process.stderr + process.stdout)
                    self.assertEqual(process.stderr, "")
                    payload = json.loads(process.stdout)
                    self.assertFalse(payload["measured"])
                    self.assertEqual(payload["state"], "UNMEASURED")
                    self.assertEqual(payload["error"], "catalog %s is not an array" % field)
                    self.assertNotIn("find_count", payload)
                    self.assertNotIn("clearance", payload)

    def test_cli_valid_catalogue_keeps_existing_status(self):
        process = subprocess.run(
            [sys.executable, "-B", str(ROOT / "host" / "finder_zero.py"),
             "--root", str(ROOT), "--catalog", str(ROOT / "ground" / "FINDER_ZERO.json")],
            cwd=ROOT, text=True, capture_output=True, timeout=10,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(process.stderr, "")
        payload = json.loads(process.stdout)
        self.assertTrue(payload["measured"])
        self.assertEqual(payload["catalog_defects"], 4)
        self.assertFalse(payload["clearance"])
        # Existing fixture's status is not a claim that this repair is published.
        self.assertEqual(payload["state"], "INTEGRATED")


if __name__ == "__main__":
    unittest.main()
