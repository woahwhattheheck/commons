#!/usr/bin/env python3
"""Independent UIOWA-108 completion-integrity regression coverage.

ZZ-KESTREL-R9V6, GPT-6 Astra Pro; OP5-KELVIN retains original builder credit.
All records are synthetic. Tests use only the standard library and temp dirs.
Run with python -B -m unittest -v test_completion_integrity; repeat with -O.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import scenario
import transition

HERE = Path(__file__).resolve().parent


def packet():
    return {
        "packet_id": "SYNTHETIC-COMPLETION-REVIEW",
        "synthetic": True,
        "authority": "FICTIONAL_REHEARSAL_ONLY",
        "transition": {"departing_ref": "SYN-PERSON-001"},
        "people": [
            {"id": "SYN-PERSON-001", "role": "contractor", "employment_type": "contractor",
             "service": "ESS", "synthetic": True},
            {"id": "SYN-PERSON-002", "role": "lead", "employment_type": "staff",
             "service": "ESS", "synthetic": True},
        ],
        "applications": [
            {"id": "SYN-APP-001", "name": "Fictional application", "service": "ESS",
             "owner_ref": "SYN-PERSON-001", "successor_ref": "SYN-PERSON-002", "synthetic": True}
        ],
        "service_identities": [], "runbooks": [],
        "access_changes": [
            {"id": "SYN-CHG-001", "subject_ref": "SYN-PERSON-001", "target_ref": "SYN-APP-001",
             "action": "REASSIGN_OWNER", "status": "COMPLETED", "completed_at": "2026-09-15",
             "evidence_ref": "synthetic://completion-review/change-001", "synthetic": True}
        ],
    }


def report(value):
    return transition.build(value)[0]


class CompletionDates(unittest.TestCase):
    def test_calendar_and_offset_timestamp_controls(self):
        for value in ("2024-02-29", "2026-09-15", "2026-09-15T12:34:56Z",
                      "2026-09-15T12:34:56.123456-04:00", "2026-09-15T12:34:56+05:30"):
            with self.subTest(value=value):
                self.assertTrue(scenario.valid_completion_date(value))
                data = packet(); data["access_changes"][0]["completed_at"] = value
                self.assertTrue(report(data).transition_closed())

    def test_date_missing_prevents_completion(self):
        data = packet(); del data["access_changes"][0]["completed_at"]
        result = report(data)
        self.assertFalse(result.transition_closed())
        self.assertEqual(result.items[0]["state"], "NO_EVIDENCE")
        self.assertIn("INVALID_COMPLETION_DATE", [i.code for i in result.issues])

    def test_blank_null_and_unknown_dates_prevent_completion(self):
        for value in (None, "", " ", "UNKNOWN"):
            with self.subTest(value=value):
                data = packet(); data["access_changes"][0]["completed_at"] = value
                self.assertFalse(report(data).transition_closed())

    def test_impossible_calendar_dates_are_not_evidence(self):
        for value in ("2026-02-29", "2026-02-30", "2026-00-01", "2026-13-01", "0000-01-01"):
            with self.subTest(value=value):
                data = packet(); data["access_changes"][0]["completed_at"] = value
                self.assertEqual(report(data).items[0]["state"], "NO_EVIDENCE")

    def test_timestamp_requires_offset_and_valid_clock(self):
        for value in ("2026-09-15T12:34:56", "2026-09-15T24:00:00Z",
                      "2026-09-15T12:60:00Z", "2026-09-15T12:34:56+24:00"):
            with self.subTest(value=value):
                self.assertFalse(scenario.valid_completion_date(value))

    def test_offset_minutes_are_not_normalized_into_another_hour(self):
        for offset in ("+00:60", "+00:99", "-01:99", "+23:60", "-23:99"):
            value = "2026-09-15T12:34:56" + offset
            with self.subTest(value=value):
                self.assertFalse(scenario.valid_completion_date(value))
                data = packet(); data["access_changes"][0]["completed_at"] = value
                self.assertFalse(report(data).transition_closed())

    def test_date_not_silently_normalized_or_coerced(self):
        for value in (20260915, True, [], {}, "2026-9-15", "20260915", " 2026-09-15",
                      "2026-09-15\n", "2026-W38-2", "２０２６-０９-１５"):
            with self.subTest(value=value):
                self.assertFalse(scenario.valid_completion_date(value))

    def test_no_unstated_today_or_assessment_cutoff(self):
        # Parsing a declared date is not certifying that an event has occurred.
        self.assertTrue(scenario.valid_completion_date("2099-01-01"))

    def test_direct_classifier_also_rejects_undated_completion(self):
        data = packet(); del data["access_changes"][0]["completed_at"]
        state, reasons, evidence = transition.classify_item(data["applications"][0], data["access_changes"], set())
        self.assertEqual(state, "NO_EVIDENCE")
        self.assertEqual(evidence, [])
        self.assertIn("valid completion date", " ".join(reasons))


class DiagnosticPropagation(unittest.TestCase):
    def assert_open_with(self, value, code):
        result = report(value)
        self.assertFalse(result.transition_closed())
        self.assertIn(code, [i.code for i in result.issues])
        return result

    def test_unknown_action_cannot_close(self):
        data = packet(); data["access_changes"][0]["action"] = "NOT_AN_ACTION"
        result = self.assert_open_with(data, "UNKNOWN_VOCABULARY_VALUE")
        self.assertEqual(result.items[0]["state"], "NO_EVIDENCE")

    def test_missing_action_does_not_raise_keyerror(self):
        data = packet(); del data["access_changes"][0]["action"]
        self.assert_open_with(data, "MISSING_REQUIRED_FIELD")

    def test_missing_null_or_blank_change_id_cannot_support_completion(self):
        for value in (None, "", " ", "MISSING"):
            with self.subTest(value=value):
                data = packet()
                if value == "MISSING":
                    del data["access_changes"][0]["id"]
                else:
                    data["access_changes"][0]["id"] = value
                result = self.assert_open_with(data, "MISSING_REQUIRED_FIELD")
                self.assertEqual(result.items[0]["state"], "NO_EVIDENCE")

    def test_nonstring_locator_does_not_raise_attributeerror(self):
        for value in ([], {}, 12, False):
            with self.subTest(value=value):
                data = packet(); data["access_changes"][0]["evidence_ref"] = value
                self.assert_open_with(data, "INVALID_FIELD_TYPE")

    def test_duplicate_change_id_does_not_silently_choose_first(self):
        data = packet(); data["access_changes"].append(copy.deepcopy(data["access_changes"][0]))
        result = self.assert_open_with(data, "DUPLICATE_RECORD_ID")
        self.assertEqual(result.items[0]["state"], "NO_EVIDENCE")

    def test_conflicting_duplicate_changes_are_not_order_dependent(self):
        data = packet(); other = copy.deepcopy(data["access_changes"][0]); other["status"] = "REQUESTED"
        data["access_changes"].append(other)
        first = report(data).as_dict()
        data["access_changes"].reverse()
        second = report(data).as_dict()
        self.assertEqual(first, second)
        self.assertFalse(first["transition_closed"])

    def test_broken_change_reference_propagates_to_target(self):
        data = packet(); data["access_changes"][0]["successor_ref"] = "SYN-PERSON-999"
        result = self.assert_open_with(data, "DANGLING_REFERENCE")
        self.assertEqual(result.items[0]["state"], "NO_EVIDENCE")

    def test_successor_must_name_a_person_not_any_resolved_record(self):
        data = packet(); data["applications"][0]["successor_ref"] = "SYN-APP-001"
        self.assert_open_with(data, "REFERENCE_KIND_MISMATCH")

    def test_invalid_successor_record_cannot_support_completion(self):
        data = packet(); del data["people"][1]["role"]
        result = self.assert_open_with(data, "MISSING_REQUIRED_FIELD")
        self.assertEqual(result.items[0]["state"], "NO_EVIDENCE")

    def test_invalid_departing_record_propagates(self):
        data = packet(); data["people"][0]["employment_type"] = "UNKNOWN"
        result = self.assert_open_with(data, "UNKNOWN_VOCABULARY_VALUE")
        self.assertEqual(result.items[0]["state"], "NO_EVIDENCE")

    def test_departing_reference_must_resolve_to_person(self):
        data = packet(); data["transition"]["departing_ref"] = "SYN-APP-001"
        self.assert_open_with(data, "REFERENCE_KIND_MISMATCH")

    def test_nonstring_reference_diagnosed_without_crash(self):
        for field in ("owner_ref", "successor_ref", "covers_app_ref"):
            with self.subTest(field=field):
                data = packet(); data["applications"][0][field] = ["SYN-PERSON-002"]
                self.assert_open_with(data, "INVALID_FIELD_TYPE")

    def test_unrelated_issue_blocks_packet_not_valid_item(self):
        data = packet(); data["people"].append({"id": "SYN-PERSON-003", "synthetic": True})
        result = self.assert_open_with(data, "MISSING_REQUIRED_FIELD")
        self.assertEqual(result.items[0]["state"], "COMPLETED")
        text = transition.render_markdown(result)
        self.assertIn("Transition NOT closed", text)
        self.assertIn("Packet issues", text)

    def test_related_invalid_change_not_hidden_by_valid_change(self):
        data = packet(); other = copy.deepcopy(data["access_changes"][0]); other["id"] = "SYN-CHG-002"
        other["completed_at"] = ""; data["access_changes"].append(other)
        result = self.assert_open_with(data, "INVALID_COMPLETION_DATE")
        self.assertEqual(result.items[0]["state"], "NO_EVIDENCE")

    def test_integrity_propagation_terminates_on_reference_cycle(self):
        data = packet(); data["people"][0]["successor_ref"] = "SYN-PERSON-002"
        data["people"][1]["successor_ref"] = "SYN-PERSON-001"; del data["people"][1]["role"]
        result = self.assert_open_with(data, "MISSING_REQUIRED_FIELD")
        self.assertTrue({"SYN-PERSON-001", "SYN-PERSON-002", "SYN-APP-001", "SYN-CHG-001"} <= result.invalid_refs)

    def test_valid_reference_cycle_does_not_manufacture_issue(self):
        data = packet(); data["people"][0]["successor_ref"] = "SYN-PERSON-002"
        data["people"][1]["successor_ref"] = "SYN-PERSON-001"
        result = report(data)
        self.assertEqual(result.issues, [])
        self.assertTrue(result.transition_closed())

    def test_missing_locator_keeps_original_distinction(self):
        data = packet(); data["access_changes"][0]["evidence_ref"] = "   "
        result = report(data)
        self.assertEqual(result.items[0]["state"], "NO_EVIDENCE")
        self.assertIn("no evidence locator", " ".join(result.items[0]["reasons"]))

    def test_requested_and_in_progress_need_no_completion_date(self):
        for status in ("REQUESTED", "IN_PROGRESS"):
            with self.subTest(status=status):
                data = packet(); data["access_changes"][0].update(status=status, completed_at=None, evidence_ref=None)
                result = report(data)
                self.assertEqual(result.issues, [])
                self.assertEqual(result.items[0]["state"], "NO_EVIDENCE")

    def test_issue_code_validation_survives_optimized_python(self):
        with self.assertRaises(ValueError):
            scenario.PacketIssue("SYN-APP-001", "UNRECOGNIZED", "field", "detail")


class MalformedStructures(unittest.TestCase):
    def test_root_must_be_object(self):
        for value in (None, [], "packet", 42, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                transition.build(value)

    def test_transition_must_be_object(self):
        for value in (None, [], "transition", 42):
            data = packet(); data["transition"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                transition.build(data)

    def test_each_section_must_be_array(self):
        for field in ("people", "applications", "service_identities", "runbooks", "access_changes"):
            for value in (None, {}, "records", 42):
                data = packet(); data[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    transition.build(data)

    def test_each_record_must_be_object(self):
        for value in (None, [], "record", 42):
            data = packet(); data["applications"].append(value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                transition.build(data)

    def test_ids_must_be_strings_before_hash_lookup(self):
        for value in ([], {}, 1, True):
            data = packet(); data["applications"][0]["id"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                transition.build(data)

    def test_empty_and_missing_transition_are_diagnostics_not_crashes(self):
        for value in ({}, {"transition": {}}):
            with self.subTest(value=value):
                result = report(value)
                self.assertFalse(result.transition_closed())
                self.assertIn("MISSING_REQUIRED_FIELD", [i.code for i in result.issues])

    def test_departing_reference_nonstring_is_diagnostic(self):
        data = packet(); data["transition"]["departing_ref"] = []
        result = report(data)
        self.assertFalse(result.transition_closed())
        self.assertIn("INVALID_FIELD_TYPE", [i.code for i in result.issues])


class CliAndStability(unittest.TestCase):
    def run_case(self, data):
        with tempfile.TemporaryDirectory(prefix="transition-review-") as tmp:
            root = Path(tmp); src = root/"input.json"; out = root/"reports"
            src.write_text(json.dumps(data), encoding="utf-8")
            before = src.read_bytes()
            flags = ["-O"] if sys.flags.optimize else []
            proc = subprocess.run([sys.executable, "-B", *flags, str(HERE/"transition.py"),
                                   "--input", str(src), "--outdir", str(out)],
                                  text=True, capture_output=True, timeout=10)
            outputs = {p.name:p.read_bytes() for p in out.iterdir()} if out.exists() else {}
            self.assertEqual(src.read_bytes(), before)
            self.assertNotIn("Traceback", proc.stderr)
            return proc, outputs

    def test_closed_exit_zero_and_three_reports(self):
        proc, outputs = self.run_case(packet())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(outputs), 3)
        self.assertTrue(json.loads(outputs["transition_report.json"])["transition_closed"])

    def test_undated_exit_one_and_visible_issue(self):
        data = packet(); del data["access_changes"][0]["completed_at"]
        proc, outputs = self.run_case(data)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        result = json.loads(outputs["transition_report.json"])
        self.assertFalse(result["transition_closed"])
        self.assertIn("INVALID_COMPLETION_DATE", [i["code"] for i in result["issues"]])

    def test_missing_action_exit_one_not_unhandled_exception(self):
        data = packet(); del data["access_changes"][0]["action"]
        proc, outputs = self.run_case(data)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertEqual(len(outputs), 3)

    def test_wrong_locator_type_exit_one(self):
        data = packet(); data["access_changes"][0]["evidence_ref"] = []
        proc, _ = self.run_case(data)
        self.assertEqual(proc.returncode, 1, proc.stderr)

    def test_wrong_shapes_exit_two_without_files(self):
        for data in ([], {"transition": None}, {"people": {}}, {"applications": [False]}):
            with self.subTest(data=data):
                proc, outputs = self.run_case(data)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertEqual(outputs, {})

    def test_nonsynthetic_record_exit_three_without_files(self):
        data = packet(); data["people"][0]["synthetic"] = False
        proc, outputs = self.run_case(data)
        self.assertEqual(proc.returncode, 3, proc.stderr)
        self.assertEqual(outputs, {})

    def test_valid_clean_report_bytes_match_published_outputs(self):
        data = json.loads((HERE/"fixtures/contractor_transition.json").read_text())
        proc, outputs = self.run_case(data)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        for name, content in outputs.items():
            self.assertEqual(content, (HERE/"sample_output"/name).read_bytes(), name)

    def test_repeat_output_bytes_are_deterministic(self):
        data = packet(); del data["access_changes"][0]["completed_at"]
        self.assertEqual(self.run_case(data)[1], self.run_case(data)[1])

    def test_build_does_not_change_source_packet(self):
        data = packet(); before = copy.deepcopy(data)
        report(data); report(data)
        self.assertEqual(data, before)

    def test_unordered_unique_records_keep_report_identical(self):
        data = json.loads((HERE/"fixtures/contractor_transition.json").read_text())
        before = report(data).as_dict()
        for field in ("people", "applications", "service_identities", "runbooks", "access_changes"):
            data[field].reverse()
        self.assertEqual(report(data).as_dict(), before)

    def test_published_fixture_digests_remain_anchored(self):
        expected = {"contractor_transition.json": "0939e7cd6c72920acc7a576d9e2070390c0b66a9",
                    "contractor_transition_unsafe.json": "3640946cb019df27d5c457fb57399b4f72919a44"}
        for filename, digest in expected.items():
            data = (HERE/"fixtures"/filename).read_bytes()
            self.assertEqual(hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest(), digest)


if __name__ == "__main__":
    unittest.main(verbosity=2)
