#!/usr/bin/env python3
"""A malformed snapshot must not hide otherwise usable work rows."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("snapshot_current_work", ROOT / "host" / "current_work.py")
cw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cw)

BAD_SNAPSHOTS = (False, True, 0, 7, 0.0, 1.5, "", "unexpected snapshot", [], [1], [["main_sha", "a" * 40]])


def catalog():
    return {
        "schema": cw.SCHEMA,
        "add_work": {"preferred": cw.SHIP_LOOP},
        "historical_directives": [],
        "items": [
            {"id": "snapshot-build-20260908", "title": "Keep buildable work visible", "kind": "BUILDABLE", "claimed_paths": ["delivered.txt"]},
            {"id": "snapshot-owner-20260908", "title": "Keep external work visible", "kind": "OWNER_PLATFORM", "claimed_paths": ["delivered.txt"]},
            {"id": "snapshot-device-20260908", "title": "Keep existing device state", "kind": "DEVICE_PINNED", "claimed_paths": []},
        ],
    }


class SnapshotShapeTests(unittest.TestCase):
    def test_nonobject_snapshots_report_once_and_keep_work_visible(self):
        for snapshot in BAD_SNAPSHOTS:
            with self.subTest(snapshot=snapshot):
                data = catalog()
                before = copy.deepcopy((data, snapshot))
                result = cw.project(data, snapshot)
                self.assertEqual(result["problems"], ["snapshot is not an object"])
                self.assertEqual([row["status"] for row in result["items"]], ["OPEN", "NEEDS_OWNER", "PINNED"])
                self.assertEqual(result["items"], result["open_now"])
                self.assertTrue(all(row["main_sha"] == "" for row in result["items"]))
                self.assertEqual((data, snapshot), before)
                json.dumps(result, allow_nan=False)

    def test_direct_reconciliation_tolerates_nonobject_snapshots(self):
        for item in catalog()["items"]:
            expected = cw.reconcile_item(item, {})
            for snapshot in BAD_SNAPSHOTS:
                with self.subTest(kind=item["kind"], snapshot=snapshot):
                    self.assertEqual(cw.reconcile_item(item, snapshot), expected)

    def test_none_is_still_an_optional_missing_snapshot(self):
        data = catalog()
        self.assertEqual(cw.project(data, None), cw.project(data, {}))
        self.assertEqual(cw.project(data, None)["problems"], [])

    def test_empty_catalog_still_reports_invalid_snapshot(self):
        data = catalog()
        data["items"] = []
        for snapshot in BAD_SNAPSHOTS:
            with self.subTest(snapshot=snapshot):
                result = cw.project(data, snapshot)
                self.assertEqual(result["items"], [])
                self.assertEqual(result["problems"], ["snapshot is not an object"])

    def test_invalid_catalog_and_snapshot_diagnostics_are_both_retained(self):
        for data in (None, [], "bad catalog", {"items": 7}):
            with self.subTest(catalog=data):
                original = cw.validate_catalog(data)
                result = cw.project(data, 7)
                self.assertEqual(result["problems"], original + ["snapshot is not an object"])
                self.assertEqual(result["items"], [])

    def test_many_rows_do_not_duplicate_snapshot_diagnostics(self):
        data = catalog()
        data["items"] = [dict(data["items"][0], id="snapshot-many-%08d" % n) for n in range(40)]
        result = cw.project(data, ["not", "a", "snapshot"])
        self.assertEqual(len(result["items"]), 40)
        self.assertEqual(result["problems"], ["snapshot is not an object"])
        self.assertEqual(result["open_now"], result["items"])

    def test_valid_main_evidence_and_existing_pin_behavior_are_unchanged(self):
        data = catalog()
        snapshot = {"main_sha": "a" * 40, "main_paths": {"delivered.txt": True}, "open_prs": [11]}
        result = cw.project(data, snapshot)
        self.assertEqual(result["problems"], [])
        self.assertEqual([row["status"] for row in result["items"]], ["CLOSED", "CLOSED", "PINNED"])
        self.assertEqual(result["open_now"], [result["items"][2]])
        self.assertFalse(result["items"][2]["executable"])

    def test_valid_dictionary_snapshots_and_catalogs_are_not_mutated(self):
        data = catalog()
        for snapshot in ({}, {"slack_text": "done"}, {"main_sha": "a" * 40, "main_paths": {"delivered.txt": True}}):
            with self.subTest(snapshot=snapshot):
                before = copy.deepcopy((data, snapshot))
                cw.project(data, snapshot)
                self.assertEqual((data, snapshot), before)

    def test_exact_sha_mixed_paths_and_chat_cannot_invent_closure(self):
        item = catalog()["items"][0]
        for snapshot in (
            {"main_sha": "a" * 40 + "\n", "main_paths": {"delivered.txt": True}},
            {"main_sha": "a" * 40, "main_paths": {}},
            {"main_sha": "a" * 40, "main_paths": ["delivered.txt"]},
            {"chat_said_done": True, "ntfy_200": True},
        ):
            with self.subTest(snapshot=snapshot):
                self.assertEqual(cw.reconcile_item(item, snapshot)["status"], "OPEN")
        mixed = dict(item, claimed_paths=["delivered.txt", None])
        self.assertEqual(cw.reconcile_item(mixed, {"main_sha": "a" * 40, "main_paths": {"delivered.txt": True}})["status"], "OPEN")

    def test_nested_metadata_problems_do_not_hide_snapshot_problem(self):
        data = catalog()
        data["add_work"] = ["route"]
        data["historical_directives"] = 7
        result = cw.project(data, "bad snapshot")
        self.assertEqual(result["problems"], ["add_work must be an object", "historical_directives must be a list", "snapshot is not an object"])
        self.assertEqual(len(result["open_now"]), 3)

    def test_cli_keeps_real_tree_success_and_metadata_failure_contracts(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "ground").mkdir()
            data = catalog()
            source = root / "ground" / "CURRENT_WORK.json"
            source.write_text(json.dumps(data), encoding="utf-8")
            (root / "delivered.txt").write_text("actual file\n", encoding="utf-8")
            command = [sys.executable, "-B", cw.__file__, "--root", str(root), "--main-sha", "a" * 40]
            completed = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stderr, "")
            result = json.loads(completed.stdout)
            self.assertEqual([r["status"] for r in result["items"]], ["CLOSED", "CLOSED", "PINNED"])
            data["add_work"] = ["bad route"]
            source.write_text(json.dumps(data), encoding="utf-8")
            completed = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(completed.returncode, 1)
            self.assertEqual(completed.stderr, "")
            self.assertEqual(json.loads(completed.stdout)["problems"], ["add_work must be an object"])


if __name__ == "__main__":
    unittest.main()
