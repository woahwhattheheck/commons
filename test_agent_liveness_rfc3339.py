#!/usr/bin/env python3
"""RFC 3339 grammar regressions for the agent-liveness timestamp boundary."""

from __future__ import annotations

import datetime as dt
import unittest

from host.agent_liveness_index import AgentLivenessError, _timestamp, build_index


UTC = dt.timezone.utc
BLOBS = {
    "presence.json": "1" * 40,
    "lastseen.json": "2" * 40,
    "claims.json": "3" * 40,
}


class AgentLivenessRfc3339Tests(unittest.TestCase):
    def assert_rfc_error(self, text: object) -> None:
        with self.assertRaisesRegex(AgentLivenessError, "must be RFC3339"):
            _timestamp(text, "stamp")

    def test_canonical_z_and_numeric_offsets_normalize_to_utc(self) -> None:
        self.assertEqual(_timestamp("2026-09-01T16:00:00Z", "stamp"), dt.datetime(2026, 9, 1, 16, tzinfo=UTC))
        self.assertEqual(_timestamp("2026-09-01T18:30:00+02:30", "stamp"), dt.datetime(2026, 9, 1, 16, tzinfo=UTC))
        self.assertEqual(_timestamp("2026-09-01T08:00:00-08:00", "stamp"), dt.datetime(2026, 9, 1, 16, tzinfo=UTC))
        self.assertEqual(_timestamp("2026-09-01T16:00:00-00:00", "stamp"), dt.datetime(2026, 9, 1, 16, tzinfo=UTC))

    def test_lowercase_t_and_z_are_permitted(self) -> None:
        expected = dt.datetime(2026, 9, 1, 16, tzinfo=UTC)
        self.assertEqual(_timestamp("2026-09-01t16:00:00z", "stamp"), expected)
        self.assertEqual(_timestamp("2026-09-01t18:30:00+02:30", "stamp"), expected)

    def test_fraction_requires_dot_and_at_least_one_ascii_digit(self) -> None:
        parsed = _timestamp("2026-09-01T16:00:00.123456789Z", "stamp")
        self.assertEqual(parsed, dt.datetime(2026, 9, 1, 16, 0, 0, 123456, tzinfo=UTC))
        for text in (
            "2026-09-01T16:00:00.Z",
            "2026-09-01T16:00:00,1Z",
            "2026-09-01T16:00:00.１２Z",
        ):
            with self.subTest(text=text):
                self.assert_rfc_error(text)

    def test_missing_timezone_keeps_specific_error(self) -> None:
        with self.assertRaisesRegex(AgentLivenessError, "must include a timezone"):
            _timestamp("2026-09-01T16:00:00", "stamp")

    def test_fromisoformat_extensions_are_rejected(self) -> None:
        rejected = (
            "2026-09-01 16:00:00+00:00",
            "2026-09-01X16:00:00+00:00",
            "20260901T160000+0000",
            "2026-W36-2T16:00:00+00:00",
            "2026-09-01T16:00+00:00",
            "2026-09-01T16:00:00+0000",
            "2026-09-01T16:00:00+00:00:30",
            "2026-09-01T16:00:00+00:00.5",
        )
        for text in rejected:
            with self.subTest(text=text):
                self.assert_rfc_error(text)

    def test_leading_trailing_and_embedded_controls_are_rejected(self) -> None:
        for text in (
            " 2026-09-01T16:00:00Z",
            "2026-09-01T16:00:00Z ",
            "2026-09-01T16:00:00Z\n",
            "2026-09-01T16:00:\x0000Z",
        ):
            with self.subTest(text=repr(text)):
                self.assert_rfc_error(text)

    def test_calendar_clock_and_offset_ranges_are_checked(self) -> None:
        rejected = (
            "0000-09-01T16:00:00Z",
            "2025-02-29T16:00:00Z",
            "2026-13-01T16:00:00Z",
            "2026-09-31T16:00:00Z",
            "2026-09-01T24:00:00Z",
            "2026-09-01T16:60:00Z",
            "2026-09-01T16:00:61Z",
            "2026-09-01T16:00:00+24:00",
            "2026-09-01T16:00:00-00:60",
        )
        for text in rejected:
            with self.subTest(text=text):
                self.assert_rfc_error(text)

    def test_leap_second_is_limited_to_utc_june_or_december_boundary(self) -> None:
        self.assertEqual(
            _timestamp("2016-12-31T23:59:60Z", "stamp"),
            dt.datetime(2017, 1, 1, tzinfo=UTC),
        )
        self.assertEqual(
            _timestamp("2016-12-31T15:59:60-08:00", "stamp"),
            dt.datetime(2017, 1, 1, tzinfo=UTC),
        )
        for text in (
            "2016-12-31T23:58:60Z",
            "2016-11-30T23:59:60Z",
            "2016-12-31T23:59:60+01:00",
        ):
            with self.subTest(text=text):
                self.assert_rfc_error(text)

    def test_blank_optional_timestamp_behavior_is_unchanged(self) -> None:
        for value in (None, "", " \t\n", False):
            with self.subTest(value=repr(value)):
                self.assertIsNone(_timestamp(value, "stamp", allow_blank=True))
        with self.assertRaisesRegex(AgentLivenessError, "must be nonempty"):
            _timestamp("", "stamp")

    def test_nonstring_values_do_not_bypass_grammar(self) -> None:
        for value in (1, True, [1], {"x": 1}):
            with self.subTest(value=repr(value)):
                self.assert_rfc_error(value)

    def test_build_index_accepts_lowercase_and_preserves_freshness(self) -> None:
        result = build_index(
            presence=[{"from": "actor", "presence": "PRESENT", "id": "r1", "ts": "2026-09-01t15:00:00z"}],
            lastseen=[{"from": "actor", "id": "r1", "ts": "2026-09-01t15:00:00z", "to": "TABLE"}],
            claims={"claims": []},
            observed_at="2026-09-01t16:00:00z",
            source_commit="a" * 40,
            source_blobs=BLOBS,
        )
        row = result["identities"][0]
        self.assertEqual(row["last_seen_at"], "2026-09-01t15:00:00z")
        self.assertEqual(row["age_seconds"], 3600)
        self.assertEqual(row["receipt_freshness"], "FRESH_6H")

    def test_source_rows_do_not_prestrip_timestamp_padding(self) -> None:
        for raw in (
            " 2026-09-01T15:00:00Z",
            "2026-09-01T15:00:00Z ",
            "2026-09-01T15:00:00Z\n",
        ):
            with self.subTest(raw=repr(raw)):
                with self.assertRaisesRegex(AgentLivenessError, r"lastseen\[actor\]\.ts must be RFC3339"):
                    build_index(
                        presence=[{"from": "actor", "presence": "PRESENT", "id": "r1", "ts": raw}],
                        lastseen=[{"from": "actor", "id": "r1", "ts": raw, "to": "TABLE"}],
                        claims={"claims": []},
                        observed_at="2026-09-01T16:00:00Z",
                        source_commit="a" * 40,
                        source_blobs=BLOBS,
                    )

    def test_source_timestamp_comparison_is_exact_before_parsing(self) -> None:
        with self.assertRaisesRegex(AgentLivenessError, "actor: timestamp mismatch"):
            build_index(
                presence=[{"from": "actor", "presence": "PRESENT", "id": "r1", "ts": " 2026-09-01T15:00:00Z"}],
                lastseen=[{"from": "actor", "id": "r1", "ts": "2026-09-01T15:00:00Z", "to": "TABLE"}],
                claims={"claims": []},
                observed_at="2026-09-01T16:00:00Z",
                source_commit="a" * 40,
                source_blobs=BLOBS,
            )

    def test_whitespace_only_source_timestamp_remains_unknown_and_normalized(self) -> None:
        result = build_index(
            presence=[{"from": "actor", "presence": "PRESENT", "id": "r1", "ts": " \t\n"}],
            lastseen=[{"from": "actor", "id": "r1", "ts": " \t\n", "to": "TABLE"}],
            claims={"claims": []},
            observed_at="2026-09-01T16:00:00Z",
            source_commit="a" * 40,
            source_blobs=BLOBS,
        )
        row = result["identities"][0]
        self.assertEqual(row["last_seen_at"], "")
        self.assertEqual(row["receipt_freshness"], "UNKNOWN_TS")
        self.assertIsNone(row["age_seconds"])

    def test_observed_at_extensions_fail_before_projection(self) -> None:
        with self.assertRaisesRegex(AgentLivenessError, "observed_at must be RFC3339"):
            build_index(
                presence=[],
                lastseen=[],
                claims={"claims": []},
                observed_at="2026-09-01 16:00:00+00:00",
                source_commit="a" * 40,
                source_blobs=BLOBS,
            )


if __name__ == "__main__":
    unittest.main()
