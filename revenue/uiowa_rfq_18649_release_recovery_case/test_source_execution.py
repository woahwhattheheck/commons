"""Real-component regressions for hashed-source execution and operator chronology.

No component outputs are mocked. Edits stay in disposable synthetic source copies.
"""
from contextlib import redirect_stderr
from copy import deepcopy
import hashlib
import importlib.util
import io
from pathlib import Path
import os
import py_compile
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("petrel109_case", HERE / "case.py")
case = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(case)


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class SourceExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="uiowa109-source-review-")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name) / "revenue"
        self.case_dir = root / HERE.name
        self.case_dir.mkdir(parents=True)
        shutil.copy2(HERE / "case.py", self.case_dir / "case.py")
        for relative, expected in case.COMPONENTS.values():
            source = HERE.parent / relative
            raw = source.read_bytes()
            self.assertEqual(git_blob(raw), expected, "Revalidate changed native components before this test")
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        old_here = case.HERE
        case.HERE = self.case_dir
        self.addCleanup(setattr, case, "HERE", old_here)
        self.environment = root / case.COMPONENTS["environment"][0]

    def cached_same_length_edit(self, old, new):
        """Reproduce the timestamp-and-length cache case with a harmless source edit."""
        raw = self.environment.read_bytes()
        changed = raw.replace(old, new, 1)
        self.assertNotEqual(raw, changed)
        self.assertEqual(len(raw), len(changed))
        seconds = 1_700_000_000
        os.utime(self.environment, (seconds, seconds))
        py_compile.compile(str(self.environment), doraise=True, optimize=sys.flags.optimize)
        self.environment.write_bytes(changed)
        os.utime(self.environment, (seconds, seconds))
        return changed

    def test_recorded_blob_is_the_executed_source_despite_valid_old_cache(self):
        changed = self.cached_same_length_edit(
            b"uiowa-environment-drift/v1", b"uiowa-environment-drift/v2")
        report = case.run(case.fixture())
        binding = report["component_bindings"]["environment"]
        self.assertEqual(binding["git_blob"], git_blob(changed))
        self.assertEqual(binding["version_binding"], "CHANGED_SINCE_TESTED_BASELINE")
        self.assertEqual(report["outputs"]["environment_at_as_of"]["schema"],
                         "uiowa-environment-drift/v2")
        self.assertEqual(report["summary"]["release_linked_recovery_minutes"], 27)

    def test_invalid_current_source_is_not_hidden_by_valid_old_cache(self):
        self.cached_same_length_edit(b'VERSION = "', b'VERSION ! "')
        with self.assertRaises(SyntaxError):
            case.load_components()

    def test_cli_reports_current_source_error_without_old_result(self):
        self.cached_same_length_edit(b'VERSION = "', b'VERSION ! "')
        errors = io.StringIO()
        with redirect_stderr(errors):
            exit_code = case.main(["--scenario", "verified"])
        self.assertEqual(exit_code, 2)
        self.assertIn("release-recovery-case:", errors.getvalue())
        self.assertIn("invalid syntax", errors.getvalue())

    def test_unedited_real_source_retains_original_three_bindings(self):
        report = case.run(case.fixture())
        self.assertEqual(len(report["component_bindings"]), 3)
        for binding in report["component_bindings"].values():
            self.assertEqual(binding["version_binding"], "EXACT_TESTED_BYTES")
        self.assertEqual(report["summary"]["release_linked_recovery_minutes"], 27)


class HistoricalWalkthroughTests(unittest.TestCase):
    def test_as_of_sequence_does_not_borrow_future_behavior(self):
        for cutoff, expected in (("09:05", None), ("09:16", None), ("09:26", None),
                                 ("09:27", None), ("09:32", 27), ("10:00", 27)):
            with self.subTest(cutoff=cutoff):
                packet = case.fixture()
                packet["as_of"] = "2026-09-18T" + cutoff + ":00Z"
                original = deepcopy(packet)
                report = case.run(packet)
                self.assertEqual(report["summary"]["release_linked_recovery_minutes"], expected)
                self.assertEqual(packet, original)
                active_refs = {r["id"] for r in report["inputs"]["recovery"]["evidence"]}
                for row in report["source_bindings"]:
                    if case.stamp(row["observed_at"]) > case.stamp(packet["as_of"]):
                        self.assertNotIn(row["event_id"], active_refs)
                if expected is None:
                    self.assertEqual(report["summary"]["verified_source_event_ids"], [])

    def test_in_flight_record_is_explicitly_excluded_not_current_health_proof(self):
        packet = case.fixture()
        packet["events"].append({"id": "A_RUNNING", "kind": "attempt",
            "at": "2026-09-18T10:10:00Z", "release_id": "REL109", "artifact_id": "ART109",
            "data": {"started_at": "2026-09-18T09:40:00Z", "strategy": "forward_repair",
                     "outcome": "completed"}})
        report = case.run(packet)
        self.assertIn({"event_id": "A_RUNNING", "reason": "AFTER_AS_OF"},
                      report["summary"]["excluded_events"])
        # This is the supported historical interval, not a new current-health claim.
        self.assertEqual(report["summary"]["release_linked_recovery_minutes"], 27)
        self.assertNotIn("current_service_health", report["summary"])


if __name__ == "__main__":
    unittest.main()
