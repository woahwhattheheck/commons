#!/usr/bin/env python3
"""Malformed catalog metadata must not hide otherwise usable current work."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent / "host"))
import current_work as cw


class NestedMetadataTests(unittest.TestCase):
    def catalog(self):
        return {
            "schema": cw.SCHEMA,
            "add_work": {"preferred": cw.SHIP_LOOP, "skill": cw.SHIP_SKILL},
            "historical_directives": [],
            "items": [
                {
                    "id": "nested-metadata-work-20260907",
                    "title": "Keep usable work visible",
                    "kind": "BUILDABLE",
                    "claimed_paths": ["delivered.txt"],
                },
                {
                    "id": "nested-metadata-device-20260907",
                    "title": "Keep existing device pin",
                    "kind": "DEVICE_PINNED",
                    "claimed_paths": [],
                },
            ],
        }

    def test_non_object_add_work_reports_problem_and_keeps_items(self):
        for value in (None, [], ["route"], "", "route", 0, 7, False, True):
            with self.subTest(value=value):
                catalog = self.catalog()
                catalog["add_work"] = value
                original = copy.deepcopy(catalog)
                result = cw.project(catalog, {})
                self.assertIn("add_work must be an object", result["problems"])
                self.assertEqual([row["status"] for row in result["items"]], ["OPEN", "PINNED"])
                self.assertEqual(result["items"], result["open_now"])
                self.assertEqual(catalog, original)

    def test_non_list_history_reports_problem_without_projecting_rows(self):
        for value in ({}, {"current": False}, "", "history", 0, 7, False, True):
            with self.subTest(value=value):
                catalog = self.catalog()
                catalog["historical_directives"] = value
                original = copy.deepcopy(catalog)
                result = cw.project(catalog, {})
                self.assertIn("historical_directives must be a list", result["problems"])
                self.assertEqual(result["historical_directives"], [])
                self.assertEqual(len(result["open_now"]), 2)
                self.assertEqual(catalog, original)

    def test_missing_or_null_optional_history_remains_accepted(self):
        for present in (False, True):
            with self.subTest(present=present):
                catalog = self.catalog()
                if present:
                    catalog["historical_directives"] = None
                else:
                    del catalog["historical_directives"]
                result = cw.project(catalog, {})
                self.assertEqual(result["problems"], [])
                self.assertEqual(result["historical_directives"], [])

    def test_history_keeps_valid_rows_and_reports_invalid_rows(self):
        catalog = self.catalog()
        row = {"n": 19, "title": "Historical work", "status_in_directives": "OPEN", "current": False}
        catalog["historical_directives"] = [row, None, "bad-row"]
        result = cw.project(catalog, {})
        self.assertEqual(result["historical_directives"], [row])
        self.assertEqual(result["problems"].count("historical row is not an object"), 2)
        self.assertEqual(result["add_work"], catalog["add_work"])

    def test_metadata_diagnostics_do_not_override_main_evidence_or_device_pin(self):
        catalog = self.catalog()
        catalog["add_work"] = ["route"]
        catalog["historical_directives"] = 7
        for main_paths, expected in (({}, "OPEN"), ({"delivered.txt": True}, "CLOSED")):
            with self.subTest(expected=expected):
                result = cw.project(catalog, {
                    "main_sha": "a" * 40,
                    "main_paths": main_paths,
                    "open_prs": [999999],
                })
                self.assertEqual(result["items"][0]["status"], expected)
                self.assertEqual(result["items"][1]["status"], "PINNED")
                self.assertFalse(result["items"][1]["executable"])
                self.assertEqual(len(result["problems"]), 2)

    def run_cli(self, catalog):
        with tempfile.TemporaryDirectory() as root:
            ground = Path(root) / "ground"
            ground.mkdir()
            (ground / "CURRENT_WORK.json").write_text(json.dumps(catalog), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(Path(cw.__file__).resolve()), "--root", root],
                capture_output=True, text=True, check=False, timeout=10,
            )

    def test_cli_returns_json_diagnostics_instead_of_traceback(self):
        for field, value, expected in (
            ("add_work", ["route"], "add_work must be an object"),
            ("historical_directives", 7, "historical_directives must be a list"),
        ):
            with self.subTest(field=field):
                catalog = self.catalog()
                catalog[field] = value
                completed = self.run_cli(catalog)
                self.assertEqual(completed.returncode, 1)
                self.assertEqual(completed.stderr, "")
                result = json.loads(completed.stdout)
                self.assertIn(expected, result["problems"])
                self.assertEqual(len(result["open_now"]), 2)

    def test_valid_cli_still_succeeds(self):
        completed = self.run_cli(self.catalog())
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        result = json.loads(completed.stdout)
        self.assertEqual(result["problems"], [])
        self.assertEqual(len(result["open_now"]), 2)


if __name__ == "__main__":
    unittest.main()
