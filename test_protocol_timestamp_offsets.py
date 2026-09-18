"""Offset timestamps retain their observed identity and projection chronology."""
from datetime import datetime, timedelta, timezone
import re
import unittest

from protocol.events import parse_event, parse_events
from protocol.schema import TS_RE


class TimestampOffsetParserTests(unittest.TestCase):
    def event(self, **fields):
        return {
            "kind": "CHECKPOINT",
            "event_id": "timestamp-offset-test-01",
            "session_id": "KESTREL_SIGMA",
            "task_id": "timestamp-offset-task-01",
            **fields,
        }

    def test_datetime_isoformat_minute_offsets_are_retained(self):
        for minutes in (-720, -300, 0, 330, 345, 840):
            with self.subTest(minutes=minutes):
                ts = datetime(2026, 9, 6, 19, 0,
                              tzinfo=timezone(timedelta(minutes=minutes))).isoformat()
                event = parse_event(self.event(ts=ts))
                self.assertEqual(event["ts"], ts)
                self.assertEqual(event["parse_state"], "OK")
                self.assertIsNotNone(re.fullmatch(TS_RE, ts))

    def test_fractional_seconds_work_with_minute_offsets(self):
        for fraction in (".1", ".123", ".123456", ".123456789"):
            for offset in ("+00:00", "-05:00", "+05:45"):
                with self.subTest(fraction=fraction, offset=offset):
                    ts = "2026-09-06T19:00:00" + fraction + offset
                    event = parse_event(self.event(ts=ts))
                    self.assertEqual(event["ts"], ts)
                    self.assertEqual(event["parse_state"], "OK")

    def test_existing_z_and_second_offset_forms_are_unchanged(self):
        for suffix in ("Z", "+00:00:00", "-05:00:00", "+05:30:15"):
            for fraction in ("", ".123456"):
                with self.subTest(suffix=suffix, fraction=fraction):
                    ts = "2026-09-06T19:00:00" + fraction + suffix
                    event = parse_event(self.event(ts=ts))
                    self.assertEqual(event["ts"], ts)
                    self.assertEqual(event["parse_state"], "OK")

    def test_timestamp_alias_accepts_the_same_offsets(self):
        ts = "2026-09-06T19:00:00-05:00"
        event = parse_event(self.event(timestamp=ts))
        self.assertEqual(event["ts"], ts)
        self.assertEqual(event["parse_state"], "OK")
        self.assertIn("timestamp", event["fields_observed"])

    def test_supplied_ids_remain_unchanged(self):
        event = parse_event(self.event(ts="2026-09-06T19:00:00+00:00"))
        self.assertEqual(event["event_id"], "timestamp-offset-test-01")
        self.assertEqual(event["session_id"], "KESTREL_SIGMA")
        self.assertEqual(event["task_id"], "timestamp-offset-task-01")

    def test_generated_ids_do_not_collapse_distinct_observation_times(self):
        raw = self.event()
        del raw["event_id"]
        first = parse_event({**raw, "ts": "2026-09-06T19:00:00+00:00"})
        second = parse_event({**raw, "ts": "2026-09-06T19:00:01+00:00"})
        self.assertNotEqual(first["event_id"], second["event_id"])
        self.assertEqual(first, parse_event({**raw, "ts": first["ts"]}))

    def test_observed_offset_is_not_rewritten_to_utc(self):
        for offset in ("+05:30", "-05:00", "-00:00"):
            with self.subTest(offset=offset):
                ts = "2026-09-06T19:00:00" + offset
                self.assertEqual(parse_event(self.event(ts=ts))["ts"], ts)

    def test_incomplete_or_extra_offset_components_stay_malformed(self):
        for suffix in ("", "+05", "+0500", "+05:3", "+5:30", "+05:30:",
                       "+05:30:0", "+05:30:00:00", "+05:30junk", "Zjunk"):
            with self.subTest(suffix=suffix):
                event = parse_event(self.event(ts="2026-09-06T19:00:00" + suffix))
                self.assertEqual(event["ts"], "UNKNOWN")
                self.assertEqual(event["parse_state"], "MALFORMED")
                self.assertEqual(event["event_id"], "timestamp-offset-test-01")

    def test_missing_timestamp_remains_optional(self):
        event = parse_event(self.event())
        self.assertEqual(event["ts"], "UNKNOWN")
        self.assertEqual(event["parse_state"], "OK")

    def test_mixed_timestamp_batch_preserves_rows(self):
        stamps = ["2026-09-06T19:00:00Z", "2026-09-06T14:00:00-05:00",
                  "2026-09-07T00:30:00+05:30", "not-a-timestamp"]
        rows = [self.event(ts=ts, event_id=f"timestamp-batch-{index:02}")
                for index, ts in enumerate(stamps)]
        result = parse_events({"events": rows})
        self.assertEqual([row["ts"] for row in result], [*stamps[:3], "UNKNOWN"])
        self.assertEqual([row["event_id"] for row in result],
                         [row["event_id"] for row in rows])


class TimestampOffsetProjectionTests(unittest.TestCase):
    def test_mixed_offsets_sort_by_instant_not_id_or_input_order(self):
        from protocol.projector import project

        # The later observation has the smaller id and is supplied first.
        later = {
            "kind": "BLOCKED", "event_id": "offset-a-later",
            "session_id": "KESTREL_SIGMA", "task_id": "offset-chronology-task",
            "ts": "2026-09-06T09:30:00-05:00",
            "blocker": {"type": "EXTERNAL_BLOCKER", "detail": "test observation"},
        }
        earlier = {
            "kind": "START", "event_id": "offset-z-earlier",
            "session_id": "KESTREL_SIGMA", "task_id": "offset-chronology-task",
            "ts": "2026-09-06T19:00:00+05:30",
        }
        result = project([later, earlier], now="2026-09-06T14:35:00Z")
        self.assertEqual([row["event_id"] for row in result["timeline"]],
                         [earlier["event_id"], later["event_id"]])
        self.assertEqual(result["sessions"][0]["state"], "BLOCKED")
        self.assertEqual(result["sessions"][0]["last_ts"], later["ts"])
        self.assertEqual(result["work_map"][0]["state"], "BLOCKED")
        self.assertEqual(result["work_map"][0]["last_ts"], later["ts"])

    def test_offset_timestamps_drive_freshness(self):
        from protocol.projector import project

        for ts, expected in (("2026-09-06T09:00:00-05:00", "WORKING"),
                             ("2026-09-06T08:00:00-05:00", "STALE")):
            with self.subTest(ts=ts):
                result = project([{
                    "kind": "START", "event_id": "offset-freshness-01",
                    "session_id": "KESTREL_SIGMA", "ts": ts,
                }], now="2026-09-06T14:00:30Z", stale_after_seconds=60)
                self.assertEqual(result["sessions"][0]["state"], expected)
                self.assertEqual(result["sessions"][0]["last_ts"], ts)


if __name__ == "__main__":
    unittest.main()
