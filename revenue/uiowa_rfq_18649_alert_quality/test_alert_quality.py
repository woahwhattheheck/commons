"""Deterministic tests of fictional records; no provider calls."""
from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import alert_quality as aq
from synthetic_history import packet


class AlertQualityTests(unittest.TestCase):
    def setUp(self):
        self.packet = packet()

    def report(self):
        return aq.analyze(self.packet)

    def row(self, iid):
        return next(r for r in self.report()["incidents"] if r["id"] == iid)

    def inc(self, iid):
        return next(r for r in self.packet["incidents"] if r["id"] == iid)

    def test_exact_sample_counts(self):
        self.assertEqual(self.report()["counts"], {
            "input_notification_rows": 18, "duplicate_export_rows": 1,
            "unique_notifications": 17, "notifications_in_window": 16,
            "notifications_outside_window": 1, "unlinked_notifications": 2,
            "recorded_incidents_in_scope": 8, "carry_in_incidents": 1,
            "repeat_notifications": 5, "escalation_notifications": 2,
            "unowned_incidents": 1, "unknown_owner_incidents": 1})

    def test_exact_response_denominator_and_median(self):
        self.assertEqual(self.report()["first_meaningful_response"], {
            "observed_count": 3, "eligible_count": 7,
            "median_seconds": 300.0, "min_seconds": 240.0, "max_seconds": 720.0})

    def test_export_duplicate_does_not_inflate_notifications(self):
        report = self.report()
        self.packet["notifications"].append(copy.deepcopy(self.packet["notifications"][0]))
        another = self.report()
        self.assertEqual(report["normalized_evidence_sha256"], another["normalized_evidence_sha256"])
        self.assertEqual(report["incidents"], another["incidents"])
        self.assertEqual(another["counts"]["duplicate_export_rows"], 2)

    def test_conflicting_duplicate_id_rejected(self):
        self.packet["notifications"][-1]["triage_seconds"] = 999
        with self.assertRaisesRegex(aq.InputError, "conflicting notification ID"):
            self.report()

    def test_same_fingerprint_separate_documented_incidents(self):
        e1, e2 = self.row("E1"), self.row("E2")
        self.assertEqual(e1["notification_count"], 3)
        self.assertEqual(e2["notification_count"], 1)
        self.assertFalse(set(e1["notification_ids"]) & set(e2["notification_ids"]))

    def test_unlinked_alerts_not_guessed_into_incidents(self):
        report = self.report()
        self.assertEqual([n["id"] for n in report["unlinked_notifications"]], ["N15", "N16"])
        self.assertEqual(len(report["incidents"]), 8)

    def test_escalation_is_not_counted_as_repeat(self):
        row = self.row("R1")
        self.assertEqual((row["notification_count"], row["repeat_count"], row["escalation_notification_count"]), (3, 1, 1))
        self.assertEqual(row["known_repeat_triage_seconds"], 0)
        self.assertEqual(row["repeat_triage_observed_count"], 0)

    def test_known_tracked_triage_not_a_savings_claim(self):
        row = self.row("E1")
        self.assertEqual((row["known_repeat_triage_seconds"], row["repeat_triage_observed_count"]), (75, 2))
        self.assertIn("not automatically wasted", " ".join(self.report()["limits"]))

    def test_acknowledgement_is_not_meaningful_response(self):
        row = self.row("R1")
        self.assertEqual(row["ack_seconds"], 60)
        self.assertIsNone(row["response_seconds"])
        self.assertEqual(row["response_state"], "right_censored")

    def test_partial_export_is_unknown_not_censored(self):
        self.assertEqual(self.row("I2")["response_state"], "unknown")
        self.assertIsNone(self.row("I2")["censor_seconds"])

    def test_resolved_without_first_action_is_unknown_not_inactivity(self):
        self.assertEqual(self.row("R2")["response_state"], "unknown")

    def test_carry_in_preserves_origin_and_excludes_new_cohort(self):
        row = self.row("R0")
        self.assertEqual(row["response_seconds"], 1200)
        self.assertEqual(row["cohort"], "carry_in")
        self.assertEqual(self.report()["groups"]["RIS"]["first_meaningful_response"]["observed_count"], 0)

    def test_future_response_does_not_leak_into_window(self):
        row = self.row("E3")
        self.assertEqual(row["response_state"], "right_censored")
        self.assertEqual(row["censor_seconds"], 60)
        self.assertIsNone(row["response_seconds"])
        self.assertEqual(row["escalation_state"], "not_due_in_window")

    def test_exact_end_notification_excluded(self):
        self.assertNotIn("N17", self.row("E3")["notification_ids"])

    def test_exact_end_response_censored(self):
        self.inc("E3")["meaningful_response"]["at"] = "2026-09-18T12:00:00Z"
        self.assertEqual(self.row("E3")["response_state"], "right_censored")

    def test_owned_and_unknown_are_distinct(self):
        self.assertEqual(self.row("R1")["owner_state"], "unowned")
        self.assertEqual(self.row("I2")["owner_state"], "unknown")

    def test_runbook_reference_does_not_prove_usefulness(self):
        self.assertTrue(self.inc("I2")["runbook"]["ref"])
        self.assertEqual(self.row("I2")["runbook_use"], "unknown")
        self.assertEqual(self.row("I1")["runbook_use"], "not_useful")

    def test_escalation_late_and_on_time(self):
        self.assertEqual(self.row("R1")["escalation_state"], "late")
        self.assertEqual(self.row("I1")["escalation_state"], "on_time")

    def test_overdue_without_event_depends_on_export_coverage(self):
        self.inc("R1")["escalation"]["at"] = None
        self.assertEqual(self.row("R1")["escalation_state"], "overdue_as_of_end")
        self.inc("R1")["lifecycle_coverage"] = "partial"
        self.assertEqual(self.row("R1")["escalation_state"], "unknown")

    def test_empty_packet_metrics_are_unknown_not_zero(self):
        self.packet["incidents"] = []
        self.packet["notifications"] = []
        report = self.report()
        self.assertIsNone(report["first_meaningful_response"]["median_seconds"])
        self.assertIsNone(report["recorded_actionability"]["fraction"])
        self.assertEqual(report["first_meaningful_response"]["eligible_count"], 0)

    def test_actionability_denominator_excludes_unknown(self):
        result = self.report()["recorded_actionability"]
        self.assertEqual((result["actionable"], result["classified_incidents"], result["unknown_incidents"]), (5, 6, 2))
        self.assertAlmostEqual(result["fraction"], 5 / 6)
        self.assertIn("not alert precision", result["interpretation"])

    def test_order_invariance(self):
        report = self.report()
        for field in ("sources", "incidents", "notifications"):
            self.packet[field].reverse()
        self.assertEqual(report, self.report())

    def test_naive_timestamp_rejected(self):
        self.inc("E1")["detected_at"] = "2026-09-18T08:00:00"
        with self.assertRaisesRegex(aq.InputError, "timezone required"):
            self.report()

    def test_equivalent_timezone_preserves_elapsed_result(self):
        self.inc("E1")["meaningful_response"]["at"] = "2026-09-18T04:05:00-04:00"
        self.assertEqual(self.row("E1")["response_seconds"], 300)

    def test_response_before_detection_rejected(self):
        self.inc("E1")["meaningful_response"]["at"] = "2026-09-18T07:59:00Z"
        with self.assertRaisesRegex(aq.InputError, "response precedes"):
            self.report()

    def test_response_before_ack_is_allowed(self):
        self.inc("E1")["ack_at"] = "2026-09-18T08:10:00Z"
        self.assertEqual(self.row("E1")["response_seconds"], 300)

    def test_response_after_resolution_rejected(self):
        self.inc("E1")["meaningful_response"]["at"] = "2026-09-18T08:25:00Z"
        with self.assertRaisesRegex(aq.InputError, "follows resolution"):
            self.report()

    def test_missing_source_reference_rejected(self):
        self.inc("E1")["source_refs"] = ["not-present"]
        with self.assertRaisesRegex(aq.InputError, "unresolved source"):
            self.report()

    def test_owned_claim_requires_support(self):
        self.inc("E1")["owner_source_refs"] = []
        with self.assertRaisesRegex(aq.InputError, "evidence reference required"):
            self.report()

    def test_usefulness_requires_task_evidence(self):
        self.inc("E1")["runbook"]["source_refs"] = []
        with self.assertRaisesRegex(aq.InputError, "evidence reference required"):
            self.report()

    def test_notification_cannot_transplant_service_scope(self):
        self.packet["notifications"][0]["service"] = "sign-in"
        with self.assertRaisesRegex(aq.InputError, "scope mismatch"):
            self.report()

    def test_unknown_incident_reference_rejected(self):
        self.packet["notifications"][0]["incident_id"] = "absent"
        with self.assertRaisesRegex(aq.InputError, "unresolved incident_id"):
            self.report()

    def test_boolean_or_nonfinite_duration_rejected(self):
        for value in (True, float("nan"), float("inf"), -1, "30"):
            with self.subTest(value=value):
                self.packet = packet()
                self.packet["notifications"][0]["triage_seconds"] = value
                with self.assertRaisesRegex(aq.InputError, "invalid triage_seconds"):
                    self.report()

    def test_duplicate_json_keys_and_constants_rejected(self):
        for value in ('{"schema_version":1,"schema_version":2}', '{"a":NaN}', '{"a":Infinity}'):
            with self.subTest(value=value), self.assertRaises(aq.InputError):
                aq.loads(value)

    def test_duplicate_incident_or_source_ids_rejected(self):
        for key in ("sources", "incidents"):
            self.packet = packet()
            self.packet[key].append(copy.deepcopy(self.packet[key][0]))
            with self.assertRaisesRegex(aq.InputError, "duplicate"):
                self.report()

    def test_recommendations_have_evidence_mechanism_effort_and_validation(self):
        source_ids = {s["id"] for s in self.packet["sources"]}
        recommendations = self.report()["recommendations"]
        self.assertTrue(recommendations)
        self.assertEqual(len({r["id"] for r in recommendations}), len(recommendations))
        for rec in recommendations:
            self.assertTrue(set(rec["source_refs"]) <= source_ids)
            self.assertTrue(rec["source_refs"])
            self.assertTrue(rec["expected_mechanism"])
            self.assertTrue(rec["validation_evidence"])
            self.assertEqual(rec["proposed_effort_hours_low_high"], sorted(rec["proposed_effort_hours_low_high"]))

    def test_csv_quotes_formula_text_and_preserves_multiline_unicode(self):
        original = [{"x": " =1+1", "y": "résumé\nA,B | sign-in"}]
        rows = list(csv.DictReader(io.StringIO(aq.csv_text(original, ["x", "y"]))))
        self.assertEqual(rows[0]["x"], "' =1+1")
        self.assertEqual(rows[0]["y"], original[0]["y"])
        self.assertEqual(original[0]["x"], " =1+1")

    def test_markdown_retains_sources_and_uncertainty(self):
        result = aq.render(self.report())
        for expected in ("SYNTHETIC REHEARSAL", "EV-E1", "synthetic_history.py#E1", "right_censored", "carry_in", "UNKNOWN"):
            self.assertIn(expected, result)

    def test_output_manifest_and_exact_json_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report"
            report = self.report()
            aq.export(report, out)
            self.assertEqual(json.loads((out / "report.json").read_text()), report)
            manifest = json.loads((out / "manifest.json").read_text())
            self.assertEqual(len(manifest["sha256"]), 4)
            for name, digest in manifest["sha256"].items():
                self.assertEqual(hashlib.sha256((out / name).read_bytes()).hexdigest(), digest)

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report"
            out.mkdir()
            sentinel = out / "report.json"
            sentinel.write_text("retained")
            with self.assertRaises(FileExistsError):
                aq.export(self.report(), out)
            self.assertEqual(sentinel.read_text(), "retained")

    def test_actual_cli_valid_and_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            input_path = base / "packet.json"
            input_path.write_text(json.dumps(self.packet), encoding="utf-8")
            command = [sys.executable, str(Path(aq.__file__)), str(input_path), "--out-dir", str(base / "out")]
            valid = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(valid.returncode, 0, valid.stderr)
            self.assertEqual(json.loads(valid.stdout)["counts"]["notifications_in_window"], 16)
            input_path.write_text('{"x":NaN}')
            invalid = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(invalid.returncode, 2)
            self.assertIn("nonfinite", invalid.stderr)
            self.assertNotIn("Traceback", invalid.stderr)


if __name__ == "__main__":
    unittest.main()
