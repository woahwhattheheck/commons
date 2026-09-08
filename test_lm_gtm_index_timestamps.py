#!/usr/bin/env python3
"""Timestamp error contracts using the complete module and real temporary ledgers."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from host import lm_gtm_index as index


UTC = dt.timezone.utc
STAMP = "2026-09-08T00:00:00Z"
OVERFLOWS = (
    "0001-01-01T00:00:00+01:00",
    "9999-12-31T23:59:59.999999-01:00",
)


class ParseTimeTests(unittest.TestCase):
    def test_json_nonstrings_are_domain_errors(self):
        for encoded in ("null", "true", "false", "0", "1", "1.5", "[]", "{}", '["date"]'):
            with self.subTest(value=encoded):
                with self.assertRaisesRegex(index.IndexError_, "invalid date-time"):
                    index.parse_time(json.loads(encoded))

    def test_bytes_are_not_coerced_to_text(self):
        with self.assertRaisesRegex(index.IndexError_, "invalid date-time"):
            index.parse_time(STAMP.encode())

    def test_invalid_text_retains_domain_error(self):
        for value in ("", "not-a-date", "2026-02-30T00:00:00Z", "2026-09-08T00:00:00+24:00"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(index.IndexError_, "invalid date-time"):
                    index.parse_time(value)

    def test_naive_text_retains_timezone_diagnostic(self):
        for value in ("2026-09-08", "2026-09-08T12:30:00"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(index.IndexError_, "^date-time must include a timezone$"):
                    index.parse_time(value)

    def test_utc_conversion_overflows_are_domain_errors(self):
        for value in OVERFLOWS:
            with self.subTest(value=value):
                with self.assertRaisesRegex(index.IndexError_, "invalid date-time") as raised:
                    index.parse_time(value)
                self.assertIsInstance(raised.exception.__cause__, OverflowError)

    def test_equivalent_offsets_preserve_microseconds(self):
        expected = dt.datetime(2026, 9, 8, 0, 0, 0, 123456, tzinfo=UTC)
        for value in (
            "2026-09-08T00:00:00.123456Z",
            "2026-09-08T05:30:00.123456+05:30",
            "2026-09-07T17:00:00.123456-07:00",
        ):
            with self.subTest(value=value):
                result = index.parse_time(value)
                self.assertEqual(result, expected)
                self.assertIs(result.tzinfo, UTC)

    def test_representable_range_endpoints_remain_valid(self):
        cases = (
            ("0001-01-01T00:00:00Z", dt.datetime.min.replace(tzinfo=UTC)),
            ("0001-01-01T01:00:00+01:00", dt.datetime.min.replace(tzinfo=UTC)),
            ("9999-12-31T23:59:59.999999Z", dt.datetime.max.replace(tzinfo=UTC)),
            ("9999-12-31T22:59:59.999999-01:00", dt.datetime.max.replace(tzinfo=UTC)),
        )
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(index.parse_time(value), expected)


class LedgerTimestampTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paths = index.default_paths(self.root)
        data = {
            "loop": {
                "schema_version": "commons-website-people-email-book/v2",
                "generated_at": STAMP,
                "prospects": [{"prospect_id": "synthetic-prospect", "organization": "Synthetic fixture", "decision": "READY_TO_DRAFT"}],
            },
            "candidates": {"generated_at": STAMP, "prospects": []},
            "funnel": {"measured_at": STAMP, "contacts": []},
            "pipeline": {"observed_at": STAMP, "current": {"research_entities": 0}},
            "inboxes": {"measured_at": STAMP},
        }
        for key, value in data.items():
            self.paths[key].parent.mkdir(parents=True, exist_ok=True)
            self.paths[key].write_text(json.dumps(value), encoding="utf-8")
        self.paths["receipts"].mkdir(parents=True)
        index.write_index(self.paths)

    def snapshot(self):
        return {path.relative_to(self.root).as_posix(): path.read_bytes()
                for path in self.root.rglob("*") if path.is_file()}

    def append(self, stamp):
        return index.append_event(subject_id="synthetic-prospect", event_id="synthetic-note-01",
                                  body="Synthetic note", ts=stamp, paths=self.paths)

    def claim(self, stamp):
        return index.claim_subject(subject_id="synthetic-prospect", owner="BEECH", ts=stamp, paths=self.paths)

    def test_append_rejects_types_without_writes(self):
        before = self.snapshot()
        for stamp in (True, 7, 1.5, ["date"], {"date": STAMP}):
            with self.subTest(stamp=stamp):
                with self.assertRaises(index.IndexError_):
                    self.append(stamp)
                self.assertEqual(self.snapshot(), before)

    def test_append_rejects_overflow_without_writes(self):
        before = self.snapshot()
        for stamp in OVERFLOWS:
            with self.subTest(stamp=stamp):
                with self.assertRaises(index.IndexError_):
                    self.append(stamp)
                self.assertEqual(self.snapshot(), before)

    def test_claim_rejects_invalid_timestamp_without_writes(self):
        before = self.snapshot()
        for stamp in (*OVERFLOWS, True, ["date"]):
            with self.subTest(stamp=stamp):
                with self.assertRaises(index.IndexError_):
                    self.claim(stamp)
                self.assertEqual(self.snapshot(), before)

    def test_release_rejects_invalid_timestamp_without_writes(self):
        self.claim("2026-09-08T01:00:00Z")
        before = self.snapshot()
        for stamp in (*OVERFLOWS, 7, {"date": STAMP}):
            with self.subTest(stamp=stamp):
                with self.assertRaises(index.IndexError_):
                    index.release_subject(subject_id="synthetic-prospect", owner="BEECH",
                                          ts=stamp, paths=self.paths)
                self.assertEqual(self.snapshot(), before)

    def test_load_events_rejects_overflow_and_preserves_jsonl(self):
        for stamp in OVERFLOWS:
            with self.subTest(stamp=stamp):
                event = {"schema_version": index.SCHEMA_VERSION, "kind": index.KIND_EVENT,
                         "id": "synthetic-note-01", "subject_id": "synthetic-prospect", "ts": stamp,
                         "type": "NOTE", "cash_usd": 0, "transport": "NONE"}
                self.paths["events"].write_text(json.dumps(event) + "\n", encoding="utf-8")
                before = self.snapshot()
                with self.assertRaises(index.IndexError_):
                    index.load_events(self.paths)
                self.assertEqual(self.snapshot(), before)

    def test_valid_append_claim_release_round_trip(self):
        event = self.append("2026-09-08T01:30:00.123456+01:00")["event"]
        self.assertEqual(event["ts"], "2026-09-08T01:30:00.123456+01:00")
        self.assertEqual(self.claim("2026-09-08T01:00:00Z")["status"], "occupied")
        self.assertEqual(index.assert_sales_owner(subject_id="synthetic-prospect", owner="BEECH",
                                                  paths=self.paths)["owner"], "BEECH")
        result = index.release_subject(subject_id="synthetic-prospect", owner="BEECH",
                                       ts="2026-09-08T02:00:00Z", paths=self.paths)
        self.assertEqual(result["status"], "released")
        with self.assertRaises(index.UnclaimedSales):
            index.assert_sales_owner(subject_id="synthetic-prospect", owner="BEECH", paths=self.paths)
        self.assertEqual(len(index.validate_index(self.paths)["events"]), 3)

    def test_freshness_threshold_unchanged(self):
        at_threshold = dt.datetime(2026, 9, 8, 12, tzinfo=UTC)
        fresh = index.composed_at_freshness(self.paths, now=at_threshold)
        stale = index.composed_at_freshness(self.paths, now=at_threshold + dt.timedelta(microseconds=1))
        self.assertEqual(fresh["status"], "FRESH")
        self.assertEqual(stale["status"], "STALE")

    def cli(self, *args):
        script = self.root / "host" / "lm_gtm_index.py"
        script.parent.mkdir(exist_ok=True)
        shutil.copyfile(index.__file__, script)
        return subprocess.run([sys.executable, str(script), *args], cwd=self.root,
                              text=True, capture_output=True, timeout=15)

    def test_cli_freshness_overflow_is_diagnostic_not_traceback(self):
        for stamp in OVERFLOWS:
            with self.subTest(stamp=stamp):
                result = self.cli("freshness", "--as-of", stamp)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertIn("invalid date-time", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_cli_valid_freshness_and_send_contract(self):
        fresh = self.cli("freshness", "--as-of", "2026-09-08T12:00:00Z")
        self.assertEqual(fresh.returncode, 0, fresh.stderr)
        self.assertEqual(json.loads(fresh.stdout)["status"], "FRESH")
        stale = self.cli("freshness", "--as-of", "2026-09-08T12:00:01Z")
        self.assertEqual(stale.returncode, 2, stale.stderr)
        self.assertEqual(json.loads(stale.stdout)["status"], "STALE")
        refused = self.cli("--send")
        self.assertEqual(refused.returncode, 3)
        self.assertIn("REFUSED live send", refused.stderr)


if __name__ == "__main__":
    unittest.main()
