#!/usr/bin/env python3
"""Receipt freshness retains all accepted fractional digits; no network calls."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

from host.agent_liveness_index import (
    AgentLivenessError, FRESH_SECONDS, RECENT_SECONDS, SOURCE_PATHS,
    build_index, canonical_text, git_blob_sha,
)

SCRIPT = Path(__file__).resolve().parent / "host" / "agent_liveness_index.py"
SOURCE_COMMIT = "a" * 40
SOURCE_BLOBS = {path: "b" * 40 for path in SOURCE_PATHS}


def documents(timestamp: str) -> dict:
    row = {"from": "CHECK", "id": "receipt-1", "ts": timestamp}
    return {
        "presence.json": [dict(row, presence="PRESENT")],
        "lastseen.json": [dict(row, to="TABLE")],
        "claims.json": {"claims": []},
    }


def build_at(timestamp: str, observed: str) -> dict:
    data = documents(timestamp)
    return build_index(
        presence=data["presence.json"], lastseen=data["lastseen.json"],
        claims=data["claims.json"], observed_at=observed,
        source_commit=SOURCE_COMMIT, source_blobs=SOURCE_BLOBS,
    )


class SubmicrosecondFreshnessTests(unittest.TestCase):
    def assert_row(self, timestamp: str, observed: str, freshness: str, age: int) -> None:
        row = build_at(timestamp, observed)["identities"][0]
        self.assertEqual(row["receipt_freshness"], freshness)
        self.assertIs(type(row["age_seconds"]), int)
        self.assertEqual(row["age_seconds"], age)
        self.assertEqual(row["last_seen_at"], timestamp)
        self.assertEqual(row["session_reachability"], "NOT_VERIFIED")
        route = "FRESH_RECEIPT_ONLY" if freshness == "FRESH_6H" else "NOT_CURRENT"
        self.assertEqual(row["routing_evidence"], route)

    def test_future_submicroseconds_are_rejected(self) -> None:
        for fraction in ("0000001", "000000001", "000000000001", "123456001"):
            observed = "2026-09-08T12:00:00." + fraction[:6] + "Z"
            with self.subTest(fraction=fraction):
                with self.assertRaisesRegex(AgentLivenessError, "in the future"):
                    build_at("2026-09-08T12:00:00." + fraction + "Z", observed)

    def test_thresholds_with_observation_remainder(self) -> None:
        observed = "2026-09-08T12:00:00.000000001Z"
        self.assert_row("2026-09-08T06:00:00Z", observed, "RECENT_24H", FRESH_SECONDS)
        self.assert_row("2026-09-07T12:00:00Z", observed, "STALE", RECENT_SECONDS)

    def test_integer_age_borrows_from_receipt_fraction(self) -> None:
        self.assert_row("2026-09-08T11:59:59.000000001Z", "2026-09-08T12:00:00Z", "FRESH_6H", 0)
        self.assert_row("2026-09-08T06:00:00.000000001Z", "2026-09-08T12:00:00Z", "FRESH_6H", FRESH_SECONDS - 1)
        self.assert_row("2026-09-07T12:00:00.000000001Z", "2026-09-08T12:00:00Z", "RECENT_24H", RECENT_SECONDS - 1)

    def test_exact_boundaries_with_equal_long_fractions(self) -> None:
        for fraction in ("000000001", "12345678901234567890123456789", "999999999"):
            observed = "2026-09-08T12:00:00." + fraction + "Z"
            for stamp, freshness, age in (
                ("2026-09-08T12:00:00", "FRESH_6H", 0),
                ("2026-09-08T06:00:00", "FRESH_6H", FRESH_SECONDS),
                ("2026-09-07T12:00:00", "RECENT_24H", RECENT_SECONDS),
            ):
                with self.subTest(fraction=fraction, age=age):
                    self.assert_row(stamp + "." + fraction + "Z", observed, freshness, age)

    def test_trailing_zero_equivalence(self) -> None:
        for left, right in (("1", "100000000"), ("000000001", "000000001000"), ("", "000000000")):
            a = "." + left if left else ""
            b = "." + right
            self.assert_row("2026-09-08T06:00:00" + a + "Z", "2026-09-08T12:00:00" + b + "Z", "FRESH_6H", FRESH_SECONDS)
            self.assert_row("2026-09-08T06:00:00" + b + "Z", "2026-09-08T12:00:00" + a + "Z", "FRESH_6H", FRESH_SECONDS)

    def test_fraction_prefix_order_is_numeric(self) -> None:
        for low, high in (("1234561", "12345610001"), ("00000009", "0000001"), ("9999998", "9999999")):
            with self.subTest(low=low, high=high):
                self.assert_row("2026-09-08T06:00:00." + low + "Z", "2026-09-08T12:00:00." + high + "Z", "RECENT_24H", FRESH_SECONDS)
                with self.assertRaisesRegex(AgentLivenessError, "in the future"):
                    build_at("2026-09-08T12:00:00." + high + "Z", "2026-09-08T12:00:00." + low + "Z")

    def test_offsets_and_lowercase_preserved(self) -> None:
        self.assert_row("2026-09-08t11:30:00.000000001+05:30", "2026-09-08t12:00:00.000000001z", "FRESH_6H", FRESH_SECONDS)
        self.assert_row("2026-09-08T01:00:00-05:00", "2026-09-08T17:30:00.000000001+05:30", "RECENT_24H", FRESH_SECONDS)
        with self.assertRaisesRegex(AgentLivenessError, "in the future"):
            build_at("2026-09-08T07:00:00.000000001-05:00", "2026-09-08T17:30:00+05:30")

    def test_leap_second_normalization_preserved(self) -> None:
        self.assert_row("2026-06-30T23:59:60.123456789Z", "2026-07-01T00:00:00.123456789Z", "FRESH_6H", 0)
        with self.assertRaisesRegex(AgentLivenessError, "in the future"):
            build_at("2026-06-30T23:59:60.123456790Z", "2026-07-01T00:00:00.123456789Z")

    def test_extreme_calendar_range_keeps_integer_age(self) -> None:
        observed = "9999-12-31T23:59:59.000000001Z"
        receipt = "0001-01-01T00:00:00.000000002Z"
        delta = dt.datetime(9999, 12, 31, 23, 59, 59) - dt.datetime(1, 1, 1)
        self.assert_row(receipt, observed, "STALE", delta.days * 86400 + delta.seconds - 1)

    def test_long_fractions_do_not_use_numeric_conversion_limits(self) -> None:
        fraction = "0" * 5000 + "1"
        with self.assertRaisesRegex(AgentLivenessError, "in the future"):
            build_at("2026-09-08T12:00:00." + fraction + "Z", "2026-09-08T12:00:00Z")
        self.assert_row("2026-09-08T06:00:00." + fraction + "Z", "2026-09-08T12:00:00." + fraction + "000Z", "FRESH_6H", FRESH_SECONDS)

    def test_unknown_receipt_unchanged(self) -> None:
        row = build_at("", "2026-09-08T12:00:00.000000001Z")["identities"][0]
        self.assertEqual(row["receipt_freshness"], "UNKNOWN_TS")
        self.assertIsNone(row["age_seconds"])

    def test_nanosecond_integer_oracle(self) -> None:
        rng = random.Random(20260908)
        origin = dt.datetime(2026, 9, 8, 12)
        scale = 10**9
        # Integer nanosecond arithmetic is independent of the production comparator.
        for index in range(240):
            threshold = rng.choice((0, 1, FRESH_SECONDS, RECENT_SECONDS))
            whole_seconds = threshold + rng.choice((-1, 0, 0, 0, 1))
            obs_fraction = rng.randrange(scale)
            receipt_fraction = rng.randrange(scale)
            observed = origin.strftime("%Y-%m-%dT%H:%M:%S") + f".{obs_fraction:09d}Z"
            receipt = (origin - dt.timedelta(seconds=whole_seconds)).strftime("%Y-%m-%dT%H:%M:%S") + f".{receipt_fraction:09d}Z"
            age_ns = whole_seconds * scale + obs_fraction - receipt_fraction
            with self.subTest(index=index, age_ns=age_ns):
                if age_ns < 0:
                    with self.assertRaisesRegex(AgentLivenessError, "in the future"):
                        build_at(receipt, observed)
                else:
                    expected = "FRESH_6H" if age_ns <= FRESH_SECONDS * scale else "RECENT_24H" if age_ns <= RECENT_SECONDS * scale else "STALE"
                    self.assert_row(receipt, observed, expected, age_ns // scale)


class SubmicrosecondCLITests(unittest.TestCase):
    def write_sources(self, root: Path, timestamp: str) -> dict[str, bytes]:
        raw = {path: canonical_text(value).encode("utf-8") for path, value in documents(timestamp).items()}
        for path, content in raw.items():
            (root / path).write_bytes(content)
        return raw

    def run_cli(self, root: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *args], text=True, capture_output=True, timeout=10, check=False)

    def test_future_rejection_preserves_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = self.write_sources(root, "2026-09-08T12:00:00.000000001Z")
            output = root / "projection.json"
            output.write_bytes(b"existing output\n")
            result = self.run_cli(root, "--observed-at", "2026-09-08T12:00:00Z", "--source-commit", SOURCE_COMMIT, "--output", str(output))
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertIn("in the future", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(output.read_bytes(), b"existing output\n")
            for path, content in raw.items():
                self.assertEqual((root / path).read_bytes(), content)

    def test_threshold_output_and_snapshot_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for receipt, freshness in (("2026-09-08T06:00:00Z", "RECENT_24H"), ("2026-09-07T12:00:00Z", "STALE")):
                with self.subTest(freshness=freshness):
                    raw = self.write_sources(root, receipt)
                    output = root / "projection.json"
                    result = self.run_cli(root, "--observed-at", "2026-09-08T12:00:00.000000001Z", "--source-commit", SOURCE_COMMIT, "--output", str(output))
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
