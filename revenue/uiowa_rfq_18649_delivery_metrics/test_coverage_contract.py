#!/usr/bin/env python3
"""Independent regression expectations for recovery, cohort and input integrity.

For the source-bound negative-control run only, UIOWA64_CALCULATOR_PATH can name
the trusted predecessor. Tests do not replace their expectations for old code.
"""
from __future__ import annotations

import csv
import importlib.util
import itertools
import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = Path(os.environ.get("UIOWA64_CALCULATOR_PATH", HERE / "calculator.py")).resolve()
spec = importlib.util.spec_from_file_location("uiowa64_coverage_target", TARGET)
if spec is None or spec.loader is None:
    raise RuntimeError("calculator module cannot be loaded")
calc = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = calc
spec.loader.exec_module(calc)

UTC = timezone.utc
START = datetime(2026, 9, 1, tzinfo=UTC)
END = datetime(2026, 9, 15, tzinfo=UTC)
DEPLOYED = START + timedelta(hours=12)
HEADER = ["deployment_id", "service", "commit_at", "deployed_at",
          "intervention_required", "recovered_at", "unplanned_rework", "notes"]
CSV_ROW = ["SYN-1", "synthetic-service", "2026-09-01T09:00:00Z",
           "2026-09-01T12:00:00Z", "false", "", "false", "SYNTHETIC only"]


def deployment(identity="SYN-1", **changes):
    base = calc.Deployment(identity, "synthetic-service", DEPLOYED - timedelta(hours=3),
                           DEPLOYED, False, None, False, "SYNTHETIC only")
    return replace(base, **changes)


def report(rows, **options):
    return calc.calculate(rows, window_start=START, window_end=END, **options)


def recovery(rows, **options):
    return report(rows, **options)["metrics"]["failed_deployment_recovery_time"]


class RecoveryContractTests(unittest.TestCase):
    def test_unknown_eligibility_does_not_hide_behind_known_recovery(self):
        result = recovery([
            deployment("SYN-FAILED", intervention_required=True,
                       recovered_at=DEPLOYED + timedelta(hours=3)),
            deployment("SYN-UNKNOWN", intervention_required=None),
        ])
        self.assertEqual(result["coverage"], {"status": "PARTIAL", "eligible": 1,
                                             "used": 1, "missing": 0, "eligibility_unknown": 1})
        self.assertEqual(result["median"], 3.0)
        self.assertEqual(result["evidence"]["unknown_failure_classification_ids"], ["SYN-UNKNOWN"])

    def test_unknown_only_is_partial_not_not_observed(self):
        result = recovery([deployment(intervention_required=None)])
        self.assertEqual(result["coverage"]["status"], "PARTIAL")
        self.assertEqual(result["coverage"]["eligible"], 0)
        self.assertEqual(result["coverage"]["eligibility_unknown"], 1)
        self.assertIsNone(result["median"])

    def test_known_non_failures_are_not_zero_hour_recoveries(self):
        result = recovery([deployment()])
        self.assertEqual(result["coverage"]["status"], "NOT_OBSERVED")
        self.assertIsNone(result["mean"])
        self.assertEqual(result["coverage"]["used"], 0)

    def test_timestamp_does_not_infer_unknown_failure_classification(self):
        result = recovery([deployment(intervention_required=None,
                                      recovered_at=DEPLOYED + timedelta(hours=3))])
        self.assertEqual(result["coverage"]["status"], "PARTIAL")
        self.assertIsNone(result["median"])
        self.assertEqual(result["evidence"]["observed_recovery_ids"], [])

    def test_missing_timestamp_and_after_cutoff_remain_separate(self):
        result = recovery([
            deployment("SYN-OBSERVED", intervention_required=True,
                       recovered_at=DEPLOYED + timedelta(hours=3)),
            deployment("SYN-MISSING", intervention_required=True),
            deployment("SYN-LATE", intervention_required=True, recovered_at=END + timedelta(days=1)),
            deployment("SYN-UNKNOWN", intervention_required=None),
        ], recovery_observed_through=END)
        self.assertEqual(result["coverage"], {"status": "PARTIAL", "eligible": 3,
                                             "used": 1, "missing": 2, "eligibility_unknown": 1})
        self.assertEqual(result["evidence"]["missing_recovery_timestamp_ids"], ["SYN-MISSING"])
        self.assertEqual(result["evidence"]["recovered_after_cutoff_ids"], ["SYN-LATE"])
        self.assertEqual(result["median"], 3.0)

    def test_recovery_cutoff_is_inclusive(self):
        result = recovery([deployment(intervention_required=True, recovered_at=END)],
                          recovery_observed_through=END)
        self.assertEqual(result["coverage"]["status"], "COMPLETE")
        self.assertEqual(result["coverage"]["used"], 1)
        self.assertEqual(result["median"], 324.0)

    def test_all_recoveries_after_cutoff_are_partial_and_null(self):
        result = recovery([deployment(intervention_required=True, recovered_at=END + timedelta(seconds=1))],
                          recovery_observed_through=END)
        self.assertEqual(result["coverage"]["status"], "PARTIAL")
        self.assertEqual(result["coverage"]["missing"], 1)
        self.assertIsNone(result["median"])

    def test_cutoff_before_deployment_window_end_is_rejected(self):
        with self.assertRaises(calc.DataError):
            report([deployment()], recovery_observed_through=END - timedelta(seconds=1))

    def test_naive_and_nondatetime_cutoffs_are_rejected(self):
        for value in (END.replace(tzinfo=None), "2026-09-15", 1, True):
            with self.subTest(value=value), self.assertRaises(calc.DataError):
                report([deployment()], recovery_observed_through=value)

    def test_retrospective_default_remains_available_and_labeled(self):
        result = report([deployment(intervention_required=True,
                                    recovered_at=END + timedelta(days=1))])
        self.assertEqual(result["scope"]["recovery_follow_up_mode"], "ALL_SUPPLIED_RECORDS_RETROSPECTIVE")
        self.assertIsNone(result["scope"]["recovery_observed_through"])
        self.assertEqual(result["metrics"]["failed_deployment_recovery_time"]["median"], 348.0)

    def test_cutoff_does_not_claim_historical_classification_or_export_completeness(self):
        result = report([deployment()], recovery_observed_through=END)
        self.assertFalse(result["interpretation_boundary"]["classification_as_of_verified"])
        self.assertFalse(result["interpretation_boundary"]["source_export_completeness_verified"])
        self.assertTrue(result["interpretation_boundary"]["recovery_statistics_are_observed_case_only"])
        self.assertEqual(result["scope"]["recovery_observed_through"], "2026-09-15T00:00:00Z")

    def test_all_three_state_cohorts_preserve_denominators_and_bounds(self):
        # 81 distinct cohorts; every failure and rework classification is exercised.
        for states in itertools.product((True, False, None), repeat=4):
            with self.subTest(states=states):
                rows = [deployment(f"SYN-{i}", intervention_required=value,
                                   recovered_at=DEPLOYED + timedelta(hours=i + 1) if value is True else None,
                                   unplanned_rework=value) for i, value in enumerate(states)]
                metrics = report(rows)["metrics"]
                positives = sum(v is True for v in states)
                unknown = sum(v is None for v in states)
                known = 4 - unknown
                for name in ("change_fail_rate", "deployment_rework_rate"):
                    metric = metrics[name]
                    bounds = metric["full_cohort_rate_bounds"]
                    self.assertEqual(metric["coverage"]["used"], known)
                    self.assertEqual(metric["coverage"]["missing"], unknown)
                    self.assertEqual(bounds["lower"], positives / 4)
                    self.assertEqual(bounds["upper"], (positives + unknown) / 4)
                    self.assertEqual(bounds["population"], 4)
                    self.assertEqual(bounds["kind"], "MISSING_CLASSIFICATION_BOUNDS_NOT_CONFIDENCE_INTERVAL")
                    self.assertEqual(metric["rate"], round(positives / known, 6) if known else None)
                coverage = metrics["failed_deployment_recovery_time"]["coverage"]
                expected_status = "PARTIAL" if unknown else ("COMPLETE" if positives else "NOT_OBSERVED")
                self.assertEqual(coverage["status"], expected_status)
                self.assertEqual(coverage["eligible"], coverage["used"] + coverage["missing"])
                self.assertEqual(coverage["eligibility_unknown"], unknown)

    def test_input_order_does_not_change_output(self):
        rows = [deployment("SYN-C", intervention_required=None), deployment("SYN-A"),
                deployment("SYN-B", intervention_required=True, recovered_at=DEPLOYED + timedelta(hours=3))]
        expected = report(rows)
        for ordering in itertools.permutations(rows):
            self.assertEqual(report(ordering), expected)

    def test_service_and_window_limits_apply_to_missingness_bounds(self):
        rows = [deployment("SYN-IN"), deployment("SYN-OTHER", service="other", intervention_required=None),
                deployment("SYN-END", deployed_at=END, intervention_required=None)]
        result = report(rows, service="synthetic-service")
        self.assertEqual(result["scope"]["deployment_count"], 1)
        self.assertEqual(result["metrics"]["change_fail_rate"]["full_cohort_rate_bounds"]["upper"], 0)

    def test_window_start_included_end_excluded(self):
        result = report([deployment("SYN-START", deployed_at=START, commit_at=START),
                         deployment("SYN-END", deployed_at=END)])
        self.assertEqual(result["scope"]["deployment_count"], 1)
        self.assertEqual(result["metrics"]["change_lead_time"]["median"], 0)


class DirectInputTests(unittest.TestCase):
    def test_boolean_values_are_not_numeric_or_textual_flags(self):
        for field in ("intervention_required", "unplanned_rework"):
            for value in (0, 1, 0.0, 1.0, "true", "false", [], {}):
                with self.subTest(field=field, value=value), self.assertRaises(calc.DataError):
                    report([deployment(**{field: value})])

    def test_duplicate_ids_rejected_even_before_filtering(self):
        for rows in ([deployment(), deployment()],
                     [deployment(), deployment(service="other")]):
            with self.subTest(rows=rows), self.assertRaises(calc.DataError):
                report(rows, service="synthetic-service")

    def test_trimmed_ids_cannot_create_hidden_duplicates(self):
        with self.assertRaises(calc.DataError):
            report([deployment("SYN-1"), deployment(" SYN-1 ")])

    def test_negative_lead_time_rejected(self):
        with self.assertRaises(calc.DataError):
            report([deployment(commit_at=DEPLOYED + timedelta(seconds=1))])

    def test_negative_recovery_time_rejected(self):
        with self.assertRaises(calc.DataError):
            report([deployment(intervention_required=True, recovered_at=DEPLOYED - timedelta(seconds=1))])

    def test_non_failure_with_recovery_is_rejected(self):
        with self.assertRaises(calc.DataError):
            report([deployment(recovered_at=DEPLOYED)])

    def test_bad_datetime_fields_rejected(self):
        for field in ("deployed_at", "commit_at", "recovered_at"):
            for value in ("2026-09-01T12:00:00Z", 1, DEPLOYED.replace(tzinfo=None)):
                with self.subTest(field=field, value=value), self.assertRaises(calc.DataError):
                    report([deployment(**{field: value})])

    def test_required_text_cannot_be_blank_or_nontext(self):
        for field in ("deployment_id", "service", "notes"):
            for value in ("", "  ", None, 42):
                with self.subTest(field=field, value=value), self.assertRaises(calc.DataError):
                    report([deployment(**{field: value})])

    def test_record_type_and_iterability_are_checked(self):
        for rows in ([{}], [None], None, 42):
            with self.subTest(rows=rows), self.assertRaises(calc.DataError):
                report(rows)

    def test_window_type_timezone_and_order_are_checked(self):
        for start, end in ((None, END), ("2026-09-01", END), (START.replace(tzinfo=None), END),
                           (START, END.replace(tzinfo=None)), (END, START), (END, END)):
            with self.subTest(start=start, end=end), self.assertRaises(calc.DataError):
                calc.calculate([deployment()], window_start=start, window_end=end)

    def test_service_filter_must_be_nonempty_text(self):
        for service in ("", "  ", 0, True):
            with self.subTest(service=service), self.assertRaises(calc.DataError):
                report([deployment()], service=service)

    def test_empty_selection_not_silently_reported_as_zero(self):
        with self.assertRaises(calc.DataError):
            report([])

    def test_generator_records_are_supported(self):
        self.assertEqual(report(iter([deployment()])), report([deployment()]))

    def test_offset_normalization_and_whitespace_match_csv_semantics(self):
        offset = timezone(timedelta(hours=-4))
        row = deployment(" SYN-1 ", service=" synthetic-service ", notes=" SYNTHETIC only ",
                         deployed_at=DEPLOYED.astimezone(offset),
                         commit_at=(DEPLOYED-timedelta(hours=3)).astimezone(offset))
        self.assertEqual(report([row]), report([deployment()]))


class CsvAndCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="uiowa64-contract-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "synthetic.csv"

    def csv_file(self, row=None, header=None):
        with self.path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(HEADER if header is None else header)
            writer.writerow(CSV_ROW if row is None else row)
        return self.path

    def cli(self, *extra):
        return subprocess.run([sys.executable, *(["-O"] if not __debug__ else []),
                               str(TARGET), str(self.path),
                               "--window-start", "2026-09-01T00:00:00Z",
                               "--window-end", "2026-09-15T00:00:00Z", *extra],
                              text=True, capture_output=True, timeout=10)

    def test_short_and_long_rows_are_data_errors(self):
        for row in (CSV_ROW[:-1], CSV_ROW + ["unheaded extra"]):
            with self.subTest(row=row), self.assertRaisesRegex(calc.DataError, "row width"):
                calc.load_deployments(self.csv_file(row))

    def test_duplicate_headers_are_rejected(self):
        with self.assertRaisesRegex(calc.DataError, "duplicate CSV columns"):
            calc.load_deployments(self.csv_file(CSV_ROW + ["overwrite"], HEADER + ["notes"]))

    def test_blank_headers_are_rejected(self):
        with self.assertRaises(calc.DataError):
            calc.load_deployments(self.csv_file(CSV_ROW + ["extra"], HEADER + [" "]))

    def test_missing_required_column_is_rejected(self):
        with self.assertRaises(calc.DataError):
            calc.load_deployments(self.csv_file(CSV_ROW[:-1], HEADER[:-1]))

    def test_empty_required_cells_are_rejected(self):
        for index in (0, 1, 3, 7):
            row = list(CSV_ROW)
            row[index] = ""
            with self.subTest(index=index), self.assertRaises(calc.DataError):
                calc.load_deployments(self.csv_file(row))

    def test_unclosed_quote_is_a_data_error(self):
        self.path.write_text(','.join(HEADER) + '\n' + ','.join(CSV_ROW[:-1]) + ',"unterminated\n')
        with self.assertRaises(calc.DataError):
            calc.load_deployments(self.path)

    def test_invalid_utf8_is_a_data_error(self):
        self.path.write_bytes((','.join(HEADER) + '\n').encode() + b'\xff')
        with self.assertRaises(calc.DataError):
            calc.load_deployments(self.path)

    def test_bom_unicode_and_multiline_notes_are_supported(self):
        row = list(CSV_ROW)
        row[-1] = 'SYNTHETIC: caf\u00e9, \u03b1\nsecond line'
        self.csv_file(row)
        self.path.write_bytes(b'\xef\xbb\xbf' + self.path.read_bytes())
        rows = calc.load_deployments(self.path)
        self.assertEqual(rows[0].notes, row[-1])
        self.assertEqual(report(rows)["scope"]["deployment_count"], 1)

    def test_csv_and_direct_api_have_identical_results(self):
        self.assertEqual(report(calc.load_deployments(self.csv_file())), report([deployment()]))

    def test_existing_named_extra_columns_remain_accepted(self):
        # Named extension columns remain source data, not calculated/exported fields.
        rows = calc.load_deployments(self.csv_file(CSV_ROW + ["SOURCE-SYN-1"], HEADER + ["source_id"]))
        self.assertEqual(report(rows), report([deployment()]))

    def test_cli_invalid_row_is_error_two_without_traceback(self):
        self.csv_file(CSV_ROW[:-1])
        proc = self.cli()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("ERROR:", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
        self.assertEqual(proc.stdout, "")

    def test_cli_output_failure_is_error_two_without_traceback(self):
        self.csv_file()
        proc = self.cli("--output", str(self.root / "absent" / "out.json"))
        self.assertEqual(proc.returncode, 2)
        self.assertNotIn("Traceback", proc.stderr)

    def test_cli_never_overwrites_input_or_file_aliases(self):
        aliases = [self.path, self.root / "symlink.csv", self.root / "hardlink.csv"]
        for index, alias in enumerate(aliases):
            with self.subTest(alias=index):
                self.csv_file()
                if index == 1:
                    alias.symlink_to(self.path)
                if index == 2:
                    os.link(self.path, alias)
                before = self.path.read_bytes()
                proc = self.cli("--output", str(alias))
                self.assertEqual(self.path.read_bytes(), before)
                self.assertEqual(proc.returncode, 2)
                self.assertIn("output must not overwrite", proc.stderr)

    def test_cli_valid_cutoff_outputs_parseable_json(self):
        self.csv_file()
        proc = self.cli("--recovery-observed-through", "2026-09-15T00:00:00Z")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout), report([deployment()], recovery_observed_through=END))

    def test_cli_output_file_contains_same_report_as_stdout(self):
        self.csv_file()
        output = self.root / "report.json"
        proc = self.cli("--output", str(output))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "")
        self.assertEqual(json.loads(output.read_text()), report([deployment()]))


if __name__ == "__main__":
    unittest.main()
