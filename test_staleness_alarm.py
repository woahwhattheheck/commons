#!/usr/bin/env python3
import io
import json
import os
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout

import host_offload.staleness_alarm as alarm


class _Response:
    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class StalenessAlarmTest(unittest.TestCase):
    def test_normalizes_dict_rows_and_applies_grace_period(self):
        payload = {
            "sinks": {
                "slack": {
                    "last_event_ts": "2026-08-23T08:00:00Z",
                    "last_git_ts": "2026-08-23T07:50:00Z",
                    "gap_seconds": 600,
                    "missing_count": 2,
                },
                "issues": {
                    "last_event_ts": "2026-08-23T08:09:00Z",
                    "last_git_ts": "2026-08-23T08:08:00Z",
                    "missing_count": 1,
                },
                "ntfy": {"gap_seconds": 9999, "missing_count": 0},
            }
        }
        got = alarm.stale_sinks(payload, now=1787472600, threshold_seconds=300)
        self.assertEqual([row["sink"] for row in got], ["slack"])
        self.assertEqual(got[0]["missing_count"], 2)

    def test_timestamp_aliases_derive_gap(self):
        payload = {
            "rows": [
                {
                    "name": "git",
                    "last_event": "2026-08-23T08:10:00Z",
                    "last_landed_in_git": "2026-08-23T08:00:00Z",
                    "missing": ["a"],
                }
            ]
        }
        got = alarm.stale_sinks(payload, now=1787472900, threshold_seconds=300)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["sink"], "git")

    def test_boolean_missing_without_timing_is_stale(self):
        got = alarm.stale_sinks(
            {"sinks": {"slack": {"missing": True}}},
            now=1787472900,
            threshold_seconds=300,
        )
        self.assertEqual(got[0]["missing_count"], 1)

    def test_codex_sol_sync_contract_states_are_authoritative(self):
        payload = {
            "schema": "commons-sync-v1",
            "sinks": [
                {
                    "name": "slack",
                    "state": "GAP",
                    "latest_source_ts": "2026-08-23T08:20:00Z",
                    "latest_durable_ts": "2026-08-23T08:00:00Z",
                    "gap_seconds": 1200,
                    "missing_count": 2,
                    "detail": "two missing",
                },
                {
                    "name": "issues",
                    "state": "UNMEASURED",
                    "gap_seconds": 9999,
                    "missing_count": 9,
                },
                {
                    "name": "git",
                    "state": "SYNCED",
                    "gap_seconds": 9999,
                    "missing_count": 9,
                },
            ],
        }
        got = alarm.stale_sinks(payload, now=1787473500, threshold_seconds=300)
        self.assertEqual(got, [{
            "sink": "slack",
            "missing_count": 2,
            "last_event": "2026-08-23T08:20:00Z",
            "last_landed_in_git": "2026-08-23T08:00:00Z",
        }])

    def test_same_bucket_and_snapshot_is_byte_identical(self):
        stale = [
            {
                "sink": "slack",
                "missing_count": 3,
                "last_event": "2026-08-23T08:00:00Z",
                "last_landed_in_git": "2026-08-23T07:00:00Z",
            }
        ]
        first = alarm.build_envelope(stale, now=1787472600)
        repeat = alarm.build_envelope(stale, now=1787473599)
        next_bucket = alarm.build_envelope(stale, now=1787475600)
        self.assertEqual(first, repeat)
        self.assertNotEqual(first["id"], next_bucket["id"])
        self.assertRegex(first["id"], r"^solder-sync-stale-\d{8}T\d{4}Z-[0-9a-f]{10}$")
        self.assertEqual(first["from"], "STALENESS_ALARM")
        self.assertEqual(first["is_language_model"], "NO")
        self.assertNotIn("permission", first["body"].lower())

    def test_carrier_is_plain_text_json_and_fails_over(self):
        calls = []

        def opener(request, timeout):
            calls.append((request, timeout))
            if len(calls) == 1:
                raise urllib.error.URLError("first down")
            return _Response(202)

        envelope = alarm.build_envelope(
            [{"sink": "slack", "missing_count": 1, "last_event": "x", "last_landed_in_git": "y"}],
            now=1787472600,
        )
        host = alarm.post_envelope(envelope, hosts=("https://one", "https://two"), opener=opener)
        self.assertEqual(host, "https://two")
        self.assertEqual(len(calls), 2)
        request = calls[1][0]
        self.assertEqual(request.headers["Content-type"], "text/plain")
        self.assertEqual(json.loads(request.data.decode("utf-8")), envelope)

    def test_missing_sync_is_quiet_and_never_calls_carrier(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = os.path.join(tmp, "sync.json")
            output = io.StringIO()
            with redirect_stdout(output):
                status = alarm.main(["--sync", missing, "--send"])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue())["state"], "QUIET")

    def test_fresh_sync_is_quiet(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sync.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"sinks": [{"sink": "slack", "missing_count": 0, "gap_seconds": 0}]}, handle)
            output = io.StringIO()
            with redirect_stdout(output):
                status = alarm.main(["--sync", path, "--now", "2026-08-23T08:20:00Z"])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue()), {"reason": "no stale sinks", "state": "QUIET"})


if __name__ == "__main__":
    unittest.main()
