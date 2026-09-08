#!/usr/bin/env python3
"""Read-only retained artifact triage, including fail-closed input mutations."""
from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile

from host import retained_battery_triage as triage

SHA = "a" * 40
BLOB = "b" * 40


def report(failed=False):
    return {
        "schema": triage.SCHEMA, "repository": "owner/repo", "run_id": "123",
        "run_attempt": "1", "checkout_sha": SHA, "event_sha": "c" * 40,
        "workflow_sha": "d" * 40, "workflow_ref": "owner/repo/.github/workflows/tests.yml@refs/pull/1/merge",
        "event_name": "pull_request", "complete": True, "problems": [],
        "workflow_outcome": "failure" if failed else "success",
        "conclusion": "FAILED" if failed else "PASSED",
        "counts": {"completed_files": 1, "passed_files": 0 if failed else 1,
                   "failed_files": 1 if failed else 0, "unresolved_source_files": 0},
        "results": [{"path": "test_example.py", "command": ["python3", "./test_example.py"],
                     "exit_code": 1 if failed else 0, "source_blob_sha": BLOB,
                     "source_in_checkout_commit": True}],
    }


class TriageTests(unittest.TestCase):
    def test_recorded_pass_is_not_current_main_verification(self):
        result = triage.triage_report(report(), SHA)
        self.assertEqual(result["status"], "RECORDED_PASS")
        self.assertFalse(result["tests_rerun"])
        self.assertFalse(result["current_checkout_verified"])
        self.assertEqual(result["provenance"]["checkout_sha"], SHA)
        self.assertEqual(result["provenance"]["event_sha"], "c" * 40)

    def test_failure_retains_original_path_exit_and_blob(self):
        result = triage.triage_report(report(True))
        self.assertEqual(result["status"], "RECORDED_FAILURES")
        self.assertEqual(result["candidate_failures"], [
            {"path": "test_example.py", "exit_code": 1, "source_blob_sha": BLOB}])

    def test_counts_cannot_be_supplied_independently_of_rows(self):
        for key in report()["counts"]:
            for value in (True, "1", -1, 999):
                with self.subTest(key=key, value=value):
                    data = report()
                    data["counts"][key] = value
                    with self.assertRaises(triage.InvalidReport):
                        triage.triage_report(data)

    def test_exit_codes_are_integers_not_booleans(self):
        for value in (True, False, 1.0, "0", None, -1, 256):
            with self.subTest(value=value):
                data = report()
                data["results"][0]["exit_code"] = value
                with self.assertRaises(triage.InvalidReport):
                    triage.triage_report(data)

    def test_duplicate_normalized_paths_are_rejected(self):
        data = report()
        row = deepcopy(data["results"][0])
        row["path"] = "./test_example.py"
        data["results"].append(row)
        with self.assertRaisesRegex(triage.InvalidReport, "duplicate"):
            triage.triage_report(data)

    def test_unsafe_or_empty_paths_are_rejected(self):
        for path in ("", ".", "../test.py", "/test.py", "a/../test.py", "a\\test.py", "a\0.py", None):
            with self.subTest(path=path):
                data = report()
                data["results"][0]["path"] = path
                with self.assertRaises(triage.InvalidReport):
                    triage.triage_report(data)

    def test_command_is_not_executed_and_must_match_path(self):
        for command in (None, "python3 test_example.py", ["bash", "./test_example.py"],
                        ["python3", "other.py"], ["python3", "./test_example.py", "extra"]):
            with self.subTest(command=command):
                data = report()
                data["results"][0]["command"] = command
                with self.assertRaises(triage.InvalidReport):
                    triage.triage_report(data)

    def test_node_record_is_supported(self):
        data = report()
        data["results"][0].update(path="test_example.js", command=["node", "test_example.js"])
        self.assertEqual(triage.triage_report(data)["status"], "RECORDED_PASS")

    def test_bad_blob_or_link_flag_is_rejected(self):
        for patch in ({"source_blob_sha": None}, {"source_blob_sha": "x" * 40},
                      {"source_blob_sha": "B" * 40}, {"source_blob_sha": "a" * 39},
                      {"source_in_checkout_commit": 1}, {"source_in_checkout_commit": False}):
            with self.subTest(patch=patch):
                data = report()
                data["results"][0].update(patch)
                with self.assertRaises(triage.InvalidReport):
                    triage.triage_report(data)

    def test_unresolved_source_is_preserved_as_hold(self):
        data = report(True)
        data["results"][0].update(source_in_checkout_commit=False, source_blob_sha=None)
        data["counts"]["unresolved_source_files"] = 1
        result = triage.triage_report(data)
        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(result["unresolved_paths"], ["test_example.py"])
        self.assertIsNone(result["candidate_failures"][0]["source_blob_sha"])

    def test_unknown_outcome_does_not_become_a_pass(self):
        data = report()
        data["workflow_outcome"] = "unknown"
        self.assertEqual(triage.triage_report(data)["status"], "HOLD")

    def test_incomplete_report_keeps_completed_failures(self):
        data = report(True)
        data.update(complete=False, conclusion="INCOMPLETE", workflow_outcome="cancelled",
                    problems=["completion marker is missing"])
        result = triage.triage_report(data)
        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(len(result["candidate_failures"]), 1)

    def test_no_tests_is_not_pass(self):
        data = report()
        data.update(results=[], conclusion="NO_TESTS")
        data["counts"] = dict.fromkeys(data["counts"], 0)
        self.assertEqual(triage.triage_report(data)["status"], "HOLD")

    def test_harness_failure_is_not_pass(self):
        data = report()
        data.update(workflow_outcome="failure", conclusion="HARNESS_FAILED")
        self.assertEqual(triage.triage_report(data)["status"], "HOLD")

    def test_reported_problem_keeps_hold(self):
        data = report()
        data["problems"] = ["retained diagnostic"]
        self.assertEqual(triage.triage_report(data)["status"], "HOLD")

    def test_bad_top_level_shapes_are_rejected(self):
        for key, value in (("schema", "other"), ("checkout_sha", ""), ("results", {}),
                           ("results", [7]), ("counts", []), ("complete", 1),
                           ("problems", "bad"), ("problems", [1]),
                           ("workflow_outcome", "green"), ("conclusion", "PASSED!")):
            with self.subTest(key=key):
                data = report()
                data[key] = value
                with self.assertRaises(triage.InvalidReport):
                    triage.triage_report(data)
        with self.assertRaises(triage.InvalidReport):
            triage.triage_report([])

    def test_complete_cancelled_or_contradictory_success_is_rejected(self):
        for data in (dict(report(), workflow_outcome="cancelled"),
                     dict(report(True), workflow_outcome="success")):
            with self.subTest(data=data):
                with self.assertRaises(triage.InvalidReport):
                    triage.triage_report(data)

    def test_checkout_pin_rejects_mismatch_and_malformed_values(self):
        for expected in ("e" * 40, "short", 17):
            with self.subTest(expected=expected):
                with self.assertRaises(triage.InvalidReport):
                    triage.triage_report(report(), expected)


class FileAndCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write_json(self, data):
        path = self.root / "report.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_json_round_trip(self):
        self.assertEqual(triage.load_report(self.write_json(report())), report())

    def test_zip_round_trip_without_extraction(self):
        path = self.root / "report.zip"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(triage.MEMBER, json.dumps(report(True)))
            archive.writestr("../must-not-extract.txt", "unused")
        self.assertEqual(triage.load_report(path), report(True))
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["report.zip"])

    def test_duplicate_or_missing_root_zip_member_is_rejected(self):
        for names in ([], ["nested/" + triage.MEMBER], [triage.MEMBER, triage.MEMBER]):
            with self.subTest(names=names):
                path = self.root / "report.zip"
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    with zipfile.ZipFile(path, "w") as archive:
                        for name in names:
                            archive.writestr(name, json.dumps(report()))
                with self.assertRaises(triage.InvalidReport):
                    triage.load_report(path)

    def test_invalid_duplicate_or_nonfinite_json_is_rejected(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'[]', b'{bad', b'\xff'):
            with self.subTest(raw=raw):
                path = self.root / "report.json"
                path.write_bytes(raw)
                with self.assertRaises(triage.InvalidReport):
                    triage.load_report(path)

    def test_bounded_json_and_zip_payloads(self):
        json_path = self.write_json(report())
        zip_path = self.root / "report.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(triage.MEMBER, json_path.read_bytes())
        with mock.patch.object(triage, "MAX_BYTES", 16):
            for path in (json_path, zip_path):
                with self.subTest(path=path):
                    with self.assertRaisesRegex(triage.InvalidReport, "byte limit"):
                        triage.load_report(path)

    def test_missing_file_is_invalid(self):
        with self.assertRaises(triage.InvalidReport):
            triage.load_report(self.root / "absent.json")

    def test_cli_exit_codes_and_machine_readable_output(self):
        held = report()
        held["workflow_outcome"] = "unknown"
        invalid = dict(report(), counts={})
        for data, code, status in ((report(), 0, "RECORDED_PASS"),
                                   (report(True), 1, "RECORDED_FAILURES"),
                                   (held, 2, "HOLD"), (invalid, 2, "INVALID")):
            with self.subTest(status=status):
                output = io.StringIO()
                with redirect_stdout(output):
                    actual = triage.main([str(self.write_json(data)), "--expect-checkout", SHA])
                self.assertEqual(actual, code)
                decoded = json.loads(output.getvalue())
                self.assertEqual(decoded["status"], status)
                self.assertFalse(decoded["tests_rerun"])


if __name__ == "__main__":
    unittest.main()
