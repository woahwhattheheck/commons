"""Non-finite Slack clocks must not become durable scan cursors."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from unittest.mock import patch

import slack_ingest as ingest


NONFINITE = (
    "NaN", "-NaN", "NaN123", "sNaN", "sNaN456",
    "Infinity", "+Infinity", "-Infinity", "inf", "-inf",
    float("nan"), float("inf"), float("-inf"),
    Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"),
)


class FiniteTimestampTests(unittest.TestCase):
    def test_event_timestamp_rejects_nonfinite_with_ingest_error(self):
        for value in NONFINITE:
            with self.subTest(value=repr(value)):
                with self.assertRaisesRegex(ingest.IngestError, "invalid Slack ts:"):
                    ingest._decimal_ts(value)

    def test_cursor_rejects_nonfinite_with_ingest_error(self):
        for value in NONFINITE:
            with self.subTest(value=repr(value)):
                with self.assertRaisesRegex(ingest.IngestError, "invalid Slack cursor:"):
                    ingest._cursor_decimal(value)

    def test_rejection_does_not_depend_on_decimal_traps(self):
        with localcontext() as context:
            context.traps[InvalidOperation] = False
            for parse in (ingest._decimal_ts, ingest._cursor_decimal):
                for value in NONFINITE:
                    with self.subTest(parser=parse.__name__, value=repr(value)):
                        with self.assertRaises(ingest.IngestError):
                            parse(value)

    def test_positive_finite_precision_and_zero_origin_are_unchanged(self):
        for value in ("1", "0.000001", "1788864203.066329", " 1788864203.066329 ",
                      Decimal("1788864203.066329000"), "1e-20", 1):
            with self.subTest(value=value):
                expected = Decimal(str(value).strip())
                self.assertEqual(ingest._decimal_ts(value).as_tuple(), expected.as_tuple())
                self.assertEqual(ingest._cursor_decimal(value).as_tuple(), expected.as_tuple())
        for value in (None, "", 0, "0", "0.000000", "-0.0"):
            with self.subTest(origin=value):
                self.assertEqual(ingest._cursor_decimal(value), Decimal(0))
        for value in ("0", "-0.0", "-1", "-0.000001", "invalid"):
            with self.subTest(timestamp=value):
                with self.assertRaises(ingest.IngestError):
                    ingest._decimal_ts(value)
        for value in ("-1", "-0.000001", "invalid"):
            with self.subTest(cursor=value):
                with self.assertRaises(ingest.IngestError):
                    ingest._cursor_decimal(value)

    def test_event_clocks_and_iso_conversion_reject_nonfinite(self):
        for value in ("NaN", "sNaN", "Infinity", "-Infinity"):
            for operation in (
                lambda: ingest.event_native_ts({"ts": value}),
                lambda: ingest.event_clock({"ts": value}),
                lambda: ingest.event_clock({"ts": "1", "edited": {"ts": value}}),
                lambda: ingest.event_native_ts({"subtype": "message_deleted", "deleted_ts": value}),
                lambda: ingest.iso_from_slack(value),
                lambda: ingest.canonical_id(value),
            ):
                with self.subTest(value=value, operation=operation):
                    with self.assertRaises(ingest.IngestError):
                        operation()
        self.assertEqual(ingest.canonical_id("1788864203.066329"), "slack-1788864203-066329")
        self.assertEqual(ingest.iso_from_slack("1.000001"), "1970-01-01T00:00:01.000001Z")

    def test_state_reader_rejects_nonfinite_without_rewriting(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.json"
            for value in ("NaN", "sNaN", "Infinity", "-Infinity", float("inf")):
                with self.subTest(value=value):
                    original = json.dumps({"cursor": value}).encode()
                    path.write_bytes(original)
                    with self.assertRaises(ingest.IngestError):
                        ingest.read_state(path)
                    self.assertEqual(path.read_bytes(), original)

    def test_state_writer_rejects_before_creating_or_replacing_files(self):
        for value in NONFINITE:
            for already_exists in (True, False):
                with self.subTest(value=repr(value), already_exists=already_exists):
                    with tempfile.TemporaryDirectory() as temporary:
                        root = Path(temporary)
                        path = root / "state.json" if already_exists else root / "absent" / "state.json"
                        original = b'{"cursor": "10.000001"}\n'
                        if already_exists:
                            path.write_bytes(original)
                        with self.assertRaises(ingest.IngestError):
                            ingest.write_state(path, value)
                        if already_exists:
                            self.assertEqual(path.read_bytes(), original)
                        else:
                            self.assertFalse(path.parent.exists())
                        self.assertFalse(path.with_name(path.name + ".tmp").exists())
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.json"
            ingest.write_state(path, "10.000002")
            self.assertEqual(ingest.read_state(path), "10.000002")

    def test_bootstrap_rejects_nonfinite_event_clock(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "posts.json"
            for value in ("NaN", "sNaN", "Infinity"):
                with self.subTest(value=value):
                    path.write_text(json.dumps({"posts": [{"id": "declared-post", "event_ts": value}]}))
                    with self.assertRaises(ingest.IngestError):
                        ingest.posts_json_high_water(path)

    def test_invalid_cursor_stops_before_slack_calls(self):
        client = ingest.SlackClient("test-placeholder")
        with patch.object(client, "call", side_effect=AssertionError("unexpected network call")) as call:
            for value in ("NaN", "sNaN", "Infinity", "-Infinity"):
                with self.subTest(value=value):
                    with self.assertRaises(ingest.IngestError):
                        client.events(value)
            call.assert_not_called()

    def test_format_cli_uses_existing_error_exit_without_traceback(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "event.json"
            for value in ("NaN", "sNaN", "Infinity"):
                with self.subTest(value=value):
                    path.write_text(json.dumps({"ts": value, "text": "offline fixture"}))
                    result = subprocess.run(
                        [sys.executable, "-B", str(Path(ingest.__file__)), "format", str(path)],
                        capture_output=True, text=True, timeout=10, check=False,
                    )
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("INGEST_ERROR: invalid Slack ts:", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
