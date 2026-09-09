"""Timestamp boundary regressions for the real GTM index module and CLI.

Run from the repository root:
    python -m unittest -v test_lm_gtm_timestamp_boundaries
All files written by these tests live in TemporaryDirectory; no network is used.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


MODULE_PATH = Path(__file__).resolve().parent / "host" / "lm_gtm_index.py"
SPEC = importlib.util.spec_from_file_location("lm_gtm_timestamp_boundary_subject", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)
UTC = dt.timezone.utc
OVERFLOW_LOW = "0001-01-01T00:00:00+01:00"
OVERFLOW_HIGH = "9999-12-31T23:59:59-01:00"
NOW = dt.datetime(2026, 9, 8, 12, tzinfo=UTC)


class ParseTimeTests(unittest.TestCase):
    def test_non_string_values_use_index_error(self) -> None:
        for value in (None, False, 7, 0.5, [], {}, b"2026-09-08T00:00:00Z"):
            with self.subTest(value=repr(value)):
                with self.assertRaises(subject.IndexError_):
                    subject.parse_time(value)

    def test_invalid_strings_keep_existing_diagnostic(self) -> None:
        for value in ("", "not-a-date", "2026-02-30T00:00:00Z", "2026-09-08T12:00:00+25:00"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(subject.IndexError_, "invalid date-time"):
                    subject.parse_time(value)

    def test_timezone_required_diagnostic_is_preserved(self) -> None:
        for value in ("2026-09-08", "2026-09-08T12:00:00"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(subject.IndexError_, "^date-time must include a timezone$"):
                    subject.parse_time(value)

    def test_lower_utc_overflow_uses_index_error(self) -> None:
        with self.assertRaisesRegex(subject.IndexError_, "invalid date-time"):
            subject.parse_time(OVERFLOW_LOW)

    def test_upper_utc_overflow_uses_index_error(self) -> None:
        with self.assertRaisesRegex(subject.IndexError_, "invalid date-time"):
            subject.parse_time(OVERFLOW_HIGH)

    def test_utc_boundaries_remain_accepted(self) -> None:
        self.assertEqual(subject.parse_time("0001-01-01T00:00:00Z"), dt.datetime.min.replace(tzinfo=UTC))
        self.assertEqual(subject.parse_time("9999-12-31T23:59:59.999999Z"), dt.datetime.max.replace(tzinfo=UTC))

    def test_offsets_near_boundaries_remain_accepted(self) -> None:
        self.assertEqual(subject.parse_time("0001-01-01T01:00:00+01:00"), dt.datetime.min.replace(tzinfo=UTC))
        self.assertEqual(subject.parse_time("9999-12-31T22:59:59.999999-01:00"), dt.datetime.max.replace(tzinfo=UTC))

    def test_offsets_and_fractional_seconds_are_preserved(self) -> None:
        values = (
            "2026-09-08T12:00:00.123456Z",
            "2026-09-08T07:00:00.123456-05:00",
            "2026-09-08T17:30:00.123456+05:30",
            "2026-09-08 12:00:00.123456+00:00",
        )
        expected = NOW.replace(microsecond=123456)
        for value in values:
            with self.subTest(value=value):
                actual = subject.parse_time(value)
                self.assertEqual(actual, expected)
                self.assertIs(actual.tzinfo, UTC)


class FileBackedTimestampTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.paths = subject.default_paths(self.root)
        self.paths["index"].parent.mkdir(parents=True)

    def write_header(self, stamp: str) -> bytes:
        raw = (json.dumps({"kind": subject.KIND_HEADER, "composed_at": stamp}) + "\n").encode()
        self.paths["index"].write_bytes(raw)
        return raw

    def write_event(self, stamp: str) -> bytes:
        event = {
            "schema_version": subject.SCHEMA_VERSION,
            "kind": subject.KIND_EVENT,
            "id": "timestamp-regression-01",
            "subject_id": "timestamp-fixture",
            "cash_usd": 0,
            "transport": "NONE",
            "ts": stamp,
            "type": "NOTE",
        }
        raw = (json.dumps(event) + "\n").encode()
        self.paths["events"].write_bytes(raw)
        return raw

    def test_saved_index_lower_overflow_is_read_only_error(self) -> None:
        original = self.write_header(OVERFLOW_LOW)
        try:
            with self.assertRaises(subject.IndexError_):
                subject.composed_at_freshness(self.paths, now=NOW)
        finally:
            self.assertEqual(self.paths["index"].read_bytes(), original)
            self.assertFalse(self.paths["state"].exists())

    def test_saved_state_upper_overflow_is_read_only_error(self) -> None:
        original = json.dumps({"composed_at": OVERFLOW_HIGH}).encode()
        self.paths["state"].write_bytes(original)
        try:
            with self.assertRaises(subject.IndexError_):
                subject.composed_at_freshness(self.paths, now=NOW)
        finally:
            self.assertEqual(self.paths["state"].read_bytes(), original)
            self.assertFalse(self.paths["index"].exists())

    def test_event_lower_overflow_is_read_only_error(self) -> None:
        original = self.write_event(OVERFLOW_LOW)
        try:
            with self.assertRaises(subject.IndexError_):
                subject.load_events(self.paths)
        finally:
            self.assertEqual(self.paths["events"].read_bytes(), original)

    def test_event_upper_overflow_is_read_only_error(self) -> None:
        original = self.write_event(OVERFLOW_HIGH)
        try:
            with self.assertRaises(subject.IndexError_):
                subject.load_events(self.paths)
        finally:
            self.assertEqual(self.paths["events"].read_bytes(), original)

    def test_valid_event_retains_original_offset_and_bytes(self) -> None:
        stamp = "2026-09-08T07:00:00.123456-05:00"
        original = self.write_event(stamp)
        rows = subject.load_events(self.paths)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ts"], stamp)
        self.assertEqual(self.paths["events"].read_bytes(), original)

    def test_freshness_at_exact_twelve_hours_is_fresh(self) -> None:
        original = self.write_header("2026-09-08T00:00:00Z")
        result = subject.composed_at_freshness(self.paths, now=NOW)
        self.assertEqual(result["status"], "FRESH")
        self.assertEqual(result["age_hours"], 12.0)
        self.assertNotIn("stale_warning", result)
        self.assertEqual(self.paths["index"].read_bytes(), original)

    def test_freshness_past_twelve_hours_is_stale(self) -> None:
        self.write_header("2026-09-08T00:00:00Z")
        result = subject.composed_at_freshness(self.paths, now=NOW + dt.timedelta(seconds=1))
        self.assertEqual(result["status"], "STALE")
        self.assertEqual(result["stale_warning"], subject.STALE_WARNING)
        self.assertEqual(result["cash_usd"], 0)

    def test_future_timestamp_stays_unknown(self) -> None:
        self.write_header("2026-09-08T12:00:01Z")
        with self.assertRaisesRegex(subject.IndexError_, "later than as_of"):
            subject.composed_at_freshness(self.paths, now=NOW)


class CliTimestampTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.script = self.root / "host" / "lm_gtm_index.py"
        self.script.parent.mkdir()
        shutil.copyfile(MODULE_PATH, self.script)
        self.index = self.root / "revenue" / "lm_gtm_index" / "INDEX.jsonl"
        self.index.parent.mkdir(parents=True)
        self.index.write_text(json.dumps({"kind": subject.KIND_HEADER, "composed_at": "2026-09-08T00:00:00Z"}) + "\n")
        self.original = self.index.read_bytes()

    def run_cli(self, stamp: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, "-B", str(self.script), "freshness", "--as-of", stamp],
            cwd=self.root, text=True, capture_output=True, timeout=10, check=False,
        )
        self.assertEqual(self.index.read_bytes(), self.original)
        return result

    def check_error(self, stamp: str) -> None:
        result = self.run_cli(stamp)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("invalid date-time", result.stderr)

    def test_cli_lower_overflow_has_diagnostic_without_traceback(self) -> None:
        self.check_error(OVERFLOW_LOW)

    def test_cli_upper_overflow_has_diagnostic_without_traceback(self) -> None:
        self.check_error(OVERFLOW_HIGH)

    def test_cli_invalid_date_retains_diagnostic(self) -> None:
        self.check_error("2026-02-30T00:00:00Z")

    def test_cli_fresh_result_preserves_exit_and_schema(self) -> None:
        result = self.run_cli("2026-09-08T07:00:00-05:00")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "FRESH")
        self.assertEqual(payload["as_of"], "2026-09-08T12:00:00Z")
        self.assertEqual(payload["age_hours"], 12.0)
        self.assertEqual(payload["cash_usd"], 0)

    def test_cli_stale_result_preserves_exit_and_warning(self) -> None:
        result = self.run_cli("2026-09-08T12:00:01Z")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, "")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "STALE")
        self.assertEqual(payload["stale_warning"], subject.STALE_WARNING)


if __name__ == "__main__":
    unittest.main()
