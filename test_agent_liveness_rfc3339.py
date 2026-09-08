#!/usr/bin/env python3
"""Strict RFC3339 syntax at the receipt-liveness timestamp boundary."""
from __future__ import annotations

import copy
import datetime as dt
import unittest

from host import agent_liveness_index as liveness
from test_agent_liveness_index import BLOBS, OBSERVED, fixture


class AgentLivenessRFC3339Tests(unittest.TestCase):
    def build(self, data: dict[str, object], observed_at: str = OBSERVED) -> dict[str, object]:
        return liveness.build_index(
            presence=data["presence"],
            lastseen=data["lastseen"],
            claims=data["claims"],
            observed_at=observed_at,
            source_commit="a" * 40,
            source_blobs=BLOBS,
        )

    def test_valid_rfc3339_forms_parse_to_utc(self) -> None:
        cases = {
            "2026-09-01T16:00:00Z": "2026-09-01T16:00:00+00:00",
            "2026-09-01t16:00:00z": "2026-09-01T16:00:00+00:00",
            "2026-09-01T16:00:00.123456Z": "2026-09-01T16:00:00.123456+00:00",
            "2026-09-01T21:30:00+05:30": "2026-09-01T16:00:00+00:00",
            "2026-09-01T08:00:00-08:00": "2026-09-01T16:00:00+00:00",
            "2026-09-01T16:00:00-00:00": "2026-09-01T16:00:00+00:00",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                parsed = liveness._timestamp(raw, "sample")
                self.assertIsNotNone(parsed)
                self.assertEqual(parsed.isoformat(), expected)
                self.assertEqual(parsed.tzinfo, dt.timezone.utc)

    def test_iso8601_extensions_are_not_mislabeled_rfc3339(self) -> None:
        invalid = (
            "2026-09-01 16:00:00+00:00",
            "20260901T160000+00:00",
            "2026-09-01X16:00:00+00:00",
            "2026-09-01T16:00:00+0000",
            "2026-09-01T16:00:00+00:00:30",
            "2026-09-01T16:00:00,5+00:00",
            "2026-W36-2T16:00:00+00:00",
        )
        for raw in invalid:
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(liveness.AgentLivenessError, "must be RFC3339"):
                    liveness._timestamp(raw, "sample")

    def test_missing_timezone_retains_specific_error(self) -> None:
        for raw in (
            "2026-09-01T16:00:00",
            "2026-09-01t16:00:00.5",
        ):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(liveness.AgentLivenessError, "must include a timezone"):
                    liveness._timestamp(raw, "sample")

    def test_observed_at_rejects_non_rfc3339_before_projection(self) -> None:
        for raw in (
            "2026-09-01 16:00:00+00:00",
            "20260901T160000+00:00",
            "2026-09-01T16:00:00+0000",
        ):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(liveness.AgentLivenessError, "observed_at must be RFC3339"):
                    self.build(fixture(), observed_at=raw)

    def test_receipt_timestamp_rejects_non_rfc3339(self) -> None:
        for raw in (
            "2026-09-01 15:00:00+00:00",
            "20260901T150000+00:00",
            "2026-09-01T15:00:00+00:00:15",
        ):
            with self.subTest(raw=raw):
                data = fixture()
                data["presence"][0]["ts"] = raw
                data["lastseen"][0]["ts"] = raw
                with self.assertRaisesRegex(
                    liveness.AgentLivenessError,
                    r"lastseen\[FRESH\]\.ts must be RFC3339",
                ):
                    self.build(data)

    def test_blank_optional_timestamp_and_freshness_boundaries_are_unchanged(self) -> None:
        data = fixture()
        result = self.build(data)
        unknown = next(row for row in result["identities"] if row["actor"] == "UNKNOWN")
        self.assertEqual(unknown["receipt_freshness"], "UNKNOWN_TS")
        self.assertIsNone(unknown["age_seconds"])

        boundary = copy.deepcopy(data)
        boundary["presence"][0]["ts"] = boundary["lastseen"][0]["ts"] = "2026-09-01T10:00:00Z"
        exact = self.build(boundary)
        fresh = next(row for row in exact["identities"] if row["actor"] == "FRESH")
        self.assertEqual(fresh["receipt_freshness"], "FRESH_6H")
        self.assertEqual(fresh["age_seconds"], 6 * 60 * 60)


if __name__ == "__main__":
    unittest.main()
