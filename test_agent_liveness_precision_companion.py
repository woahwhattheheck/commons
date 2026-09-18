#!/usr/bin/env python3
"""Exact fractional freshness boundaries on the real projection and CLI."""

from __future__ import annotations

import copy
import datetime as dt
from fractions import Fraction
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from host.agent_liveness_index import AgentLivenessError, build_index, canonical_text


BLOBS = {"presence.json": "1" * 40, "lastseen.json": "2" * 40, "claims.json": "3" * 40}
BASE = dt.datetime(2026, 9, 8, 12, tzinfo=dt.timezone.utc)
FRACTIONS = ("", "0", "0000000", "0000001", "0000009", "1234567",
             "12345670000", "1234568", "9999999", "999999999999999999")
SECOND_DELTAS = (-1, 0, 1, 21599, 21600, 21601, 86399, 86400, 86401)
ORACLE_CASES = len(FRACTIONS) ** 2 * len(SECOND_DELTAS)


def stamp(base: dt.datetime, digits: str = "") -> str:
    return base.strftime("%Y-%m-%dT%H:%M:%S") + ("." + digits if digits else "") + "Z"


def fixture(receipt: str) -> dict:
    row = {"from": "FIXTURE", "id": "fixture-receipt", "ts": receipt}
    return {"presence": [dict(row, presence="PRESENT")],
            "lastseen": [dict(row, to="TABLE")], "claims": {"claims": []}}


def build(observed: str, receipt: str) -> dict:
    return build_index(**fixture(receipt), observed_at=observed,
                       source_commit="a" * 40, source_blobs=BLOBS)


def identity(observed: str, receipt: str) -> dict:
    return build(observed, receipt)["identities"][0]


def fraction(digits: str) -> Fraction:
    return Fraction(int(digits or "0"), 10 ** len(digits))


class AgentLivenessSubmicrosecondTests(unittest.TestCase):
    def test_future_below_one_microsecond_is_rejected(self) -> None:
        for observed, receipt in (("", "0000001"), ("1234567", "1234568"),
                                  ("00000001", "000000011")):
            with self.subTest(observed=observed, receipt=receipt):
                with self.assertRaisesRegex(AgentLivenessError, "in the future"):
                    build(stamp(BASE, observed), stamp(BASE, receipt))

    def test_past_below_one_microsecond_has_zero_age(self) -> None:
        row = identity(stamp(BASE, "1234568"), stamp(BASE, "1234567"))
        self.assertEqual((row["receipt_freshness"], row["age_seconds"]), ("FRESH_6H", 0))

    def test_just_over_six_hours_is_recent_not_fresh(self) -> None:
        result = build(stamp(BASE, "0000001"), stamp(BASE - dt.timedelta(hours=6)))
        row = result["identities"][0]
        self.assertEqual((row["receipt_freshness"], row["age_seconds"]), ("RECENT_24H", 21600))
        self.assertEqual(row["routing_evidence"], "NOT_CURRENT")
        self.assertEqual(result["summary"]["fresh_6h"], 0)
        self.assertEqual(result["summary"]["recent_6_to_24h"], 1)

    def test_just_over_twenty_four_hours_is_stale(self) -> None:
        result = build(stamp(BASE, "0000001"), stamp(BASE - dt.timedelta(days=1)))
        row = result["identities"][0]
        self.assertEqual((row["receipt_freshness"], row["age_seconds"]), ("STALE", 86400))
        self.assertEqual(result["summary"]["stale_over_24h"], 1)

    def test_exact_thresholds_remain_inclusive(self) -> None:
        for seconds, expected in ((21600, "FRESH_6H"), (86400, "RECENT_24H")):
            with self.subTest(seconds=seconds):
                row = identity(stamp(BASE, "12345670000"),
                               stamp(BASE - dt.timedelta(seconds=seconds), "1234567"))
                self.assertEqual((row["receipt_freshness"], row["age_seconds"]), (expected, seconds))

    def test_just_under_thresholds_floor_to_previous_second(self) -> None:
        for seconds, expected in ((21600, "FRESH_6H"), (86400, "RECENT_24H")):
            with self.subTest(seconds=seconds):
                row = identity(stamp(BASE), stamp(BASE - dt.timedelta(seconds=seconds), "0000001"))
                self.assertEqual((row["receipt_freshness"], row["age_seconds"]), (expected, seconds - 1))

    def test_subsecond_age_does_not_round_up(self) -> None:
        row = identity(stamp(BASE + dt.timedelta(seconds=1)), stamp(BASE, "0000001"))
        self.assertEqual(row["age_seconds"], 0)
        self.assertIsInstance(row["age_seconds"], int)

    def test_trailing_zero_padding_does_not_change_instant(self) -> None:
        for observed, receipt in (("0000000100", "00000001"),
                                  ("00000001", "0000000100"), ("", "000000000")):
            with self.subTest(observed=observed, receipt=receipt):
                self.assertEqual(identity(stamp(BASE, observed), stamp(BASE, receipt))["age_seconds"], 0)

    def test_arbitrary_precision_does_not_require_bigint_conversion(self) -> None:
        digits = "0" * 5000 + "1"
        with self.assertRaisesRegex(AgentLivenessError, "in the future"):
            build(stamp(BASE), stamp(BASE, digits))
        row = identity(stamp(BASE, digits), stamp(BASE - dt.timedelta(hours=6)))
        self.assertEqual(row["receipt_freshness"], "RECENT_24H")
        equal = identity(stamp(BASE, digits + "000"), stamp(BASE, digits))
        self.assertEqual(equal["age_seconds"], 0)

    def test_numeric_timezone_offsets_and_lowercase_preserve_precision(self) -> None:
        with self.assertRaisesRegex(AgentLivenessError, "in the future"):
            build("2026-09-08t07:00:00.1234567-05:00", "2026-09-08T14:30:00.1234568+02:30")
        row = identity("2026-09-08t07:00:00.1234568-05:00", "2026-09-08t12:00:00.1234567z")
        self.assertEqual(row["age_seconds"], 0)
        row = identity("2026-09-08T07:00:00.0000001-05:00", "2026-09-08T08:30:00+02:30")
        self.assertEqual(row["receipt_freshness"], "RECENT_24H")

    def test_supported_leap_second_normalization_preserves_tail(self) -> None:
        with self.assertRaisesRegex(AgentLivenessError, "in the future"):
            build("2017-01-01T00:00:00Z", "2016-12-31T23:59:60.0000001Z")
        row = identity("2017-01-01T00:00:00.00000010Z", "2016-12-31T15:59:60.0000001-08:00")
        self.assertEqual(row["age_seconds"], 0)

    def test_exact_fraction_oracle_grid(self) -> None:
        checked = 0
        for seconds in SECOND_DELTAS:
            for observed_digits in FRACTIONS:
                for receipt_digits in FRACTIONS:
                    observed = stamp(BASE, observed_digits)
                    receipt = stamp(BASE - dt.timedelta(seconds=seconds), receipt_digits)
                    age = seconds + fraction(observed_digits) - fraction(receipt_digits)
                    context = (seconds, observed_digits, receipt_digits)
                    if age < 0:
                        with self.assertRaisesRegex(AgentLivenessError, "in the future", msg=str(context)):
                            build(observed, receipt)
                    else:
                        row = identity(observed, receipt)
                        freshness = "FRESH_6H" if age <= 21600 else "RECENT_24H" if age <= 86400 else "STALE"
                        self.assertEqual((row["receipt_freshness"], row["age_seconds"]),
                                         (freshness, age.numerator // age.denominator), context)
                    checked += 1
        self.assertEqual(checked, ORACLE_CASES)

    def test_inputs_and_raw_timestamp_metadata_are_preserved(self) -> None:
        observed, receipt = stamp(BASE, "1234568"), stamp(BASE, "1234567")
        data = fixture(receipt)
        before = copy.deepcopy(data)
        result = build_index(**data, observed_at=observed, source_commit="a" * 40, source_blobs=BLOBS)
        self.assertEqual(data, before)
        self.assertEqual(result["observed_at"], observed)
        self.assertEqual(result["identities"][0]["last_seen_at"], receipt)
        self.assertEqual(result["source_blobs"], BLOBS)
        self.assertEqual(result["schema"], "commons-agent-receipt-liveness/v1")
        self.assertEqual(json.loads(canonical_text(result)), result)

    def test_unknown_timestamp_remains_unknown(self) -> None:
        row = identity(stamp(BASE, "0000001"), " \t\n")
        self.assertEqual(row["receipt_freshness"], "UNKNOWN_TS")
        self.assertIsNone(row["age_seconds"])
        self.assertEqual(row["last_seen_at"], "")

    def _cli(self, directory: Path, *args: str) -> subprocess.CompletedProcess:
        source = Path(__file__).parent / "host" / "agent_liveness_index.py"
        return subprocess.run([sys.executable, "-B", str(source), "--root", str(directory), *args],
                              text=True, capture_output=True, timeout=10)

    def _write_sources(self, directory: Path, receipt: str) -> dict[str, bytes]:
        data = fixture(receipt)
        for name in ("presence", "lastseen", "claims"):
            (directory / (name + ".json")).write_text(json.dumps(data[name]), encoding="utf-8")
        return {name: (directory / name).read_bytes() for name in BLOBS}

    def test_real_cli_write_and_check_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            before = self._write_sources(directory, stamp(BASE - dt.timedelta(hours=6)))
            output = directory / "index.json"
            result = self._cli(directory, "--observed-at", stamp(BASE, "0000001"),
                               "--source-commit", "a" * 40, "--output", str(output))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            self.assertEqual(json.loads(output.read_text())["summary"]["recent_6_to_24h"], 1)
            checked = self._cli(directory, "--check", str(output))
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertEqual(checked.stdout.strip(), "MATCH 1 identities 0 fresh 0 stale 0 unknown")
            self.assertEqual(before, {name: (directory / name).read_bytes() for name in BLOBS})

    def test_real_cli_future_receipt_has_structured_error_and_no_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            before = self._write_sources(directory, stamp(BASE, "0000001"))
            output = directory / "index.json"
            result = self._cli(directory, "--observed-at", stamp(BASE),
                               "--source-commit", "a" * 40, "--output", str(output))
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("last-seen timestamp is in the future", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertFalse(output.exists())
            self.assertEqual(before, {name: (directory / name).read_bytes() for name in BLOBS})


if __name__ == "__main__":
    unittest.main()
