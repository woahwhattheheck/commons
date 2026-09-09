#!/usr/bin/env python3
"""Exact receipt freshness boundaries and CLI compatibility; no live sessions."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from host.agent_liveness_index import (
    AgentLivenessError,
    FRESH_SECONDS,
    RECENT_SECONDS,
    SOURCE_PATHS,
    build_index,
    canonical_text,
    git_blob_sha,
)


UTC = dt.timezone.utc
OBSERVED = dt.datetime(2026, 9, 6, 12, 0, 0, tzinfo=UTC)
SOURCE_COMMIT = "a" * 40
SOURCE_BLOBS = {name: "b" * 40 for name in SOURCE_PATHS}
SCRIPT = Path(__file__).resolve().parent / "host" / "agent_liveness_index.py"


def documents(timestamp: str) -> dict[str, object]:
    row = {"from": "CONTROL", "id": "receipt-1", "ts": timestamp}
    return {
        "presence.json": [dict(row, presence="PRESENT")],
        "lastseen.json": [dict(row, to="TABLE")],
        "claims.json": {"claims": []},
    }


def build_at(timestamp: str, observed: str = OBSERVED.isoformat()) -> dict:
    data = documents(timestamp)
    return build_index(
        presence=data["presence.json"],
        lastseen=data["lastseen.json"],
        claims=data["claims.json"],
        observed_at=observed,
        source_commit=SOURCE_COMMIT,
        source_blobs=SOURCE_BLOBS,
    )


class FractionalFreshnessTests(unittest.TestCase):
    def assert_age(self, age_us: int, freshness: str, seconds: int) -> None:
        stamp = (OBSERVED - dt.timedelta(microseconds=age_us)).isoformat()
        index = build_at(stamp)
        row = index["identities"][0]
        self.assertEqual(row["receipt_freshness"], freshness)
        self.assertIs(type(row["age_seconds"]), int)
        self.assertEqual(row["age_seconds"], seconds)
        route = "FRESH_RECEIPT_ONLY" if freshness == "FRESH_6H" else "NOT_CURRENT"
        self.assertEqual(row["routing_evidence"], route)
        self.assertEqual(row["session_reachability"], "NOT_VERIFIED")
        key = {"FRESH_6H": "fresh_6h", "RECENT_24H": "recent_6_to_24h", "STALE": "stale_over_24h"}[freshness]
        self.assertEqual(index["summary"][key], 1)
        self.assertEqual(index["source_blobs"], SOURCE_BLOBS)

    def test_subsecond_future_is_rejected(self) -> None:
        for us in (1, 500000, 999999):
            with self.subTest(future_microseconds=us):
                stamp = (OBSERVED + dt.timedelta(microseconds=us)).isoformat()
                with self.assertRaisesRegex(AgentLivenessError, "in the future"):
                    build_at(stamp)

    def test_whole_second_future_is_still_rejected(self) -> None:
        stamp = (OBSERVED + dt.timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(AgentLivenessError, "in the future"):
            build_at(stamp)

    def test_exact_boundaries_remain_inclusive(self) -> None:
        for seconds, expected in ((0, "FRESH_6H"), (FRESH_SECONDS, "FRESH_6H"), (RECENT_SECONDS, "RECENT_24H")):
            with self.subTest(age_seconds=seconds):
                self.assert_age(seconds * 1000000, expected, seconds)

    def test_fractional_ages_before_thresholds(self) -> None:
        for seconds, expected in ((FRESH_SECONDS, "FRESH_6H"), (RECENT_SECONDS, "RECENT_24H")):
            with self.subTest(threshold=seconds):
                self.assert_age(seconds * 1000000 - 1, expected, seconds - 1)

    def test_fractional_ages_after_fresh_threshold(self) -> None:
        for us in (1, 500000, 999999):
            with self.subTest(past_threshold_microseconds=us):
                self.assert_age(FRESH_SECONDS * 1000000 + us, "RECENT_24H", FRESH_SECONDS)

    def test_fractional_ages_after_recent_threshold(self) -> None:
        for us in (1, 500000, 999999):
            with self.subTest(past_threshold_microseconds=us):
                self.assert_age(RECENT_SECONDS * 1000000 + us, "STALE", RECENT_SECONDS)

    def test_positive_fractional_age_keeps_integer_schema(self) -> None:
        self.assert_age(1999999, "FRESH_6H", 1)

    def test_fractional_observation_across_day_boundary(self) -> None:
        observed = "2026-09-06T23:59:59.999999Z"
        with self.assertRaisesRegex(AgentLivenessError, "in the future"):
            build_at("2026-09-07T00:00:00Z", observed)

    def test_timezone_offsets_preserve_exact_boundaries(self) -> None:
        for hours, minutes in ((5, 30), (-7, 0), (0, 0)):
            zone = dt.timezone(dt.timedelta(hours=hours, minutes=minutes))
            observed = OBSERVED.astimezone(zone).isoformat()
            with self.subTest(offset=observed):
                future = (OBSERVED + dt.timedelta(microseconds=1)).astimezone(zone).isoformat()
                with self.assertRaisesRegex(AgentLivenessError, "in the future"):
                    build_at(future, observed)
                for seconds, expected in ((FRESH_SECONDS, "RECENT_24H"), (RECENT_SECONDS, "STALE")):
                    stamp = (OBSERVED - dt.timedelta(seconds=seconds, microseconds=1)).astimezone(zone).isoformat()
                    self.assertEqual(build_at(stamp, observed)["identities"][0]["receipt_freshness"], expected)

    def test_unknown_timestamp_stays_unknown(self) -> None:
        row = build_at("")["identities"][0]
        self.assertIsNone(row["age_seconds"])
        self.assertEqual(row["receipt_freshness"], "UNKNOWN_TS")
        self.assertEqual(row["routing_evidence"], "NOT_CURRENT")

    def test_large_elapsed_time_uses_exact_whole_seconds(self) -> None:
        observed = "9999-12-31T23:59:59.999999+00:00"
        row = build_at("0001-01-01T00:00:00+00:00", observed)["identities"][0]
        delta = dt.datetime.fromisoformat(observed) - dt.datetime(1, 1, 1, tzinfo=UTC)
        self.assertEqual(row["age_seconds"], delta.days * 86400 + delta.seconds)
        self.assertEqual(row["receipt_freshness"], "STALE")


class FractionalFreshnessCLITests(unittest.TestCase):
    def write_sources(self, root: Path, timestamp: str) -> dict[str, bytes]:
        raw = {path: canonical_text(value).encode("utf-8") for path, value in documents(timestamp).items()}
        for path, content in raw.items():
            (root / path).write_bytes(content)
        return raw

    def run_cli(self, root: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), *args],
            text=True, capture_output=True, timeout=10, check=False,
        )

    def test_cli_future_rejection_does_not_replace_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.write_sources(root, "2026-09-06T12:00:00.000001Z")
            output = root / "projection.json"
            output.write_bytes(b"existing output\n")
            result = self.run_cli(root, "--observed-at", OBSERVED.isoformat(), "--source-commit", SOURCE_COMMIT, "--output", str(output))
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertIn("in the future", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(output.read_bytes(), b"existing output\n")
            for path, content in raw.items():
                self.assertEqual((root / path).read_bytes(), content)

    def test_cli_threshold_projection_and_check_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for seconds, freshness in ((FRESH_SECONDS, "RECENT_24H"), (RECENT_SECONDS, "STALE")):
                with self.subTest(threshold=seconds):
                    stamp = (OBSERVED - dt.timedelta(seconds=seconds, microseconds=1)).isoformat()
                    raw = self.write_sources(root, stamp)
                    output = root / "projection.json"
                    result = self.run_cli(root, "--observed-at", OBSERVED.isoformat(), "--source-commit", SOURCE_COMMIT, "--output", str(output))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    projection = json.loads(output.read_text(encoding="utf-8"))
                    self.assertEqual(projection["identities"][0]["receipt_freshness"], freshness)
                    self.assertEqual(projection["source_blobs"], {path: git_blob_sha(content) for path, content in raw.items()})
                    checked = self.run_cli(root, "--check", str(output))
                    self.assertEqual(checked.returncode, 0, checked.stderr)
                    self.assertTrue(checked.stdout.startswith("MATCH 1 identities 0 fresh "), checked.stdout)
                    for path, content in raw.items():
                        self.assertEqual((root / path).read_bytes(), content)


if __name__ == "__main__":
    unittest.main()
