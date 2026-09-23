"""Malformed catalog inputs must not disappear or become evidenced durations."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "uiowa047_input_assessor", ROOT / "test_data_assessor.py"
)
if SPEC is None or SPEC.loader is None:
    raise ImportError("Cannot load the retained UIOWA-047 assessor")
assessor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(assessor)


class CatalogInputTests(unittest.TestCase):
    def row(self, **fields):
        return {"dataset_id": "SYN-INPUT", "service": "ESS",
                "purpose": "Fictional catalog input boundary", **fields}

    def payload(self, **fields):
        return {"as_of": "2026-09-19", "datasets": [self.row(**fields)]}

    def check(self, check_id, **fields):
        report = assessor.evaluate_catalog(self.payload(**fields))
        return next(c for c in report["datasets"][0]["checks"]
                    if c["check_id"] == check_id)

    def command(self):
        return [sys.executable, *(["-O"] if sys.flags.optimize else []),
                "-B", str(ROOT / "test_data_assessor.py")]

    def test_library_rejects_non_object_catalogs(self):
        for value in (None, True, 0, "catalog", [], [self.row()]):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "top-level JSON value"):
                    assessor.evaluate_catalog(value)

    def test_as_of_requires_an_exact_calendar_date(self):
        for value in (None, True, 20260919, {}, [], {"date": "2026-09-19"},
                      "", "20260919", "2026-W38-6", "2026-02-30",
                      "2026-09-19trailing-garbage", "2026-09-19T00:00:00Z"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "ISO date"):
                    assessor.evaluate_catalog({"as_of": value, "datasets": []})

    def test_exact_dates_and_empty_catalogs_remain_supported(self):
        for value in ("2026-09-19", "2024-02-29", "0001-01-01", "9999-12-31"):
            with self.subTest(value=value):
                report = assessor.evaluate_catalog({"as_of": value, "datasets": []})
                self.assertEqual(report["as_of"], value)
                self.assertEqual(report["dataset_count"], 0)
                self.assertEqual(sum(report["summary"].values()), 0)

    def test_datasets_requires_an_array(self):
        for value in (None, False, 1, "rows", {}):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "'datasets' array"):
                    assessor.evaluate_catalog({"as_of": "2026-09-19", "datasets": value})

    def test_malformed_rows_are_named_not_silently_dropped(self):
        for bad in (None, True, False, 0, 1.5, "row", [], [self.row()]):
            with self.subTest(bad=bad):
                payload = {"as_of": "2026-09-19", "datasets": [self.row(), bad, self.row()]}
                original = deepcopy(payload)
                with self.assertRaisesRegex(ValueError, r"datasets\[1\].*JSON object"):
                    assessor.evaluate_catalog(payload)
                self.assertEqual(payload, original)

    def test_all_object_rows_are_retained_even_with_missing_evidence(self):
        payload = {"as_of": "2026-09-19", "datasets": [{}, self.row()]}
        report = assessor.evaluate_catalog(payload)
        self.assertEqual(report["dataset_count"], 2)
        self.assertEqual(report["datasets"][0]["dataset_id"], "UNNAMED")
        self.assertEqual(report["summary"][assessor.UNKNOWN], 14)
        self.assertEqual(report["summary"][assessor.OBSERVED_GAP], 0)

    def test_boolean_refresh_cadences_are_unknown_not_days(self):
        for value in (False, True):
            with self.subTest(value=value):
                result = self.check("refresh_freshness", last_refreshed="2026-09-19",
                                    refresh_cadence_days=value)
                self.assertEqual(result["state"], assessor.UNKNOWN)
                self.assertNotIn("day cadence", result["detail"])

    def test_integer_cadence_boundary_and_staleness_are_preserved(self):
        at_boundary = self.check("refresh_freshness", last_refreshed="2026-09-18",
                                 refresh_cadence_days=1)
        overdue = self.check("refresh_freshness", last_refreshed="2026-09-17",
                             refresh_cadence_days=1)
        self.assertEqual(at_boundary["state"], assessor.EVIDENCED)
        self.assertEqual(overdue["state"], assessor.OBSERVED_GAP)

    def test_boolean_retention_is_an_invalid_supplied_value(self):
        for value in (False, True):
            with self.subTest(value=value):
                result = self.check("retention", retention_days=value)
                self.assertEqual(result["state"], assessor.OBSERVED_GAP)
                self.assertIn("Invalid retention_days value", result["detail"])

    def test_legitimate_zero_and_positive_retention_remain_evidenced(self):
        for value in (0, 1, 30):
            with self.subTest(value=value):
                result = self.check("retention", retention_days=value)
                self.assertEqual(result["state"], assessor.EVIDENCED)
                self.assertIn(f"{value} days", result["detail"])

    def test_missing_retention_remains_unknown_not_invalid(self):
        self.assertEqual(self.check("retention")["state"], assessor.UNKNOWN)
        self.assertEqual(self.check("retention", retention_days=None)["state"], assessor.UNKNOWN)

    def test_bad_optional_date_shapes_remain_unknown_without_crashing(self):
        for value in ({"date": "2026-09-19"}, ["2026-09-19"], True, 20260919,
                      "2026-09-19junk", "2026-09-19T12:00:00Z", "2026-W38-6"):
            with self.subTest(value=value):
                refreshed = self.check("refresh_freshness", last_refreshed=value,
                                       refresh_cadence_days=30)
                cleaned = self.check("cleanup", cleanup_required=True,
                                     cleanup_last_verified=value)
                self.assertEqual(refreshed["state"], assessor.UNKNOWN)
                self.assertEqual(cleaned["state"], assessor.UNKNOWN)

    def test_cli_input_errors_do_not_emit_or_overwrite_a_report(self):
        cases = [
            (b"{", "Expecting"),
            (b"null", "top-level JSON value"),
            (b'\xff', "decode"),
            (json.dumps({"as_of": "2026-09-19", "datasets": [None]}).encode(), "datasets[0]"),
            (json.dumps({"as_of": "2026-09-19junk", "datasets": []}).encode(), "ISO date"),
            (json.dumps({"as_of": "2026-09-19", "datasets": {}}).encode(), "'datasets' array"),
        ]
        with tempfile.TemporaryDirectory(prefix="uiowa047-input-cli-") as tmp:
            source = Path(tmp) / "catalog.json"
            output = Path(tmp) / "existing-report.json"
            sentinel = b"EXISTING OUTPUT - PRESERVE\n"
            for raw, fragment in cases:
                with self.subTest(fragment=fragment):
                    source.write_bytes(raw)
                    output.write_bytes(sentinel)
                    result = subprocess.run(
                        [*self.command(), str(source), "--format", "json", "--output", str(output)],
                        capture_output=True, text=True, timeout=20, check=False,
                    )
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertEqual(result.stdout, "")
                    self.assertIn(fragment, result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(source.read_bytes(), raw)
                    self.assertEqual(output.read_bytes(), sentinel)

    def test_cli_missing_input_is_a_readable_error(self):
        with tempfile.TemporaryDirectory(prefix="uiowa047-missing-cli-") as tmp:
            source = Path(tmp) / "missing.json"
            result = subprocess.run([*self.command(), str(source)], capture_output=True,
                                    text=True, timeout=20, check=False)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("error:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(result.stdout, "")

    def test_cli_valid_empty_catalog_is_not_an_input_error(self):
        with tempfile.TemporaryDirectory(prefix="uiowa047-empty-cli-") as tmp:
            source = Path(tmp) / "empty.json"
            source.write_text(json.dumps({"as_of": "2026-09-19", "datasets": []}), encoding="utf-8")
            result = subprocess.run([*self.command(), str(source), "--format", "json"],
                                    capture_output=True, text=True, timeout=20, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["dataset_count"], 0)


if __name__ == "__main__":
    unittest.main()
