#!/usr/bin/env python3
"""Absolute-time boundary regressions for the agent-liveness projection."""
from __future__ import annotations

import contextlib
import datetime as dt
import io
from pathlib import Path
import tempfile
import unittest

from host.agent_liveness_index import (
    AgentLivenessError,
    _timestamp,
    build_index,
    main,
)


UTC = dt.timezone.utc
BLOBS = {
    "presence.json": "1" * 40,
    "lastseen.json": "2" * 40,
    "claims.json": "3" * 40,
}


class AbsoluteTimeBoundaryTests(unittest.TestCase):
    def test_unknown_negative_zero_offset_is_not_an_absolute_instant(self) -> None:
        for text in (
            "2026-09-01T16:00:00-00:00",
            "2026-09-01t16:00:00.123-00:00",
        ):
            with self.subTest(text=text):
                with self.assertRaisesRegex(AgentLivenessError, "known UTC offset"):
                    _timestamp(text, "stamp")

    def test_unknown_offset_cannot_create_fresh_routing_evidence(self) -> None:
        stamp = "2026-09-01T15:00:00-00:00"
        with self.assertRaisesRegex(AgentLivenessError, r"lastseen\[actor\]\.ts must use a known UTC offset"):
            build_index(
                presence=[{"from": "actor", "presence": "PRESENT", "id": "r1", "ts": stamp}],
                lastseen=[{"from": "actor", "id": "r1", "ts": stamp, "to": "TABLE"}],
                claims={"claims": []},
                observed_at="2026-09-01T16:00:00Z",
                source_commit="a" * 40,
                source_blobs=BLOBS,
            )

    def test_known_offsets_still_normalize_to_utc(self) -> None:
        expected = dt.datetime(2026, 9, 1, 16, tzinfo=UTC)
        for text in (
            "2026-09-01T16:00:00Z",
            "2026-09-01t16:00:00z",
            "2026-09-01T18:30:00+02:30",
            "2026-09-01T08:00:00-08:00",
        ):
            with self.subTest(text=text):
                self.assertEqual(_timestamp(text, "stamp"), expected)

    def test_extreme_offset_underflow_is_structured(self) -> None:
        with self.assertRaisesRegex(AgentLivenessError, "must be RFC3339"):
            _timestamp("0001-01-01T00:00:00+23:59", "stamp")

    def test_extreme_offset_overflow_is_structured(self) -> None:
        with self.assertRaisesRegex(AgentLivenessError, "must be RFC3339"):
            _timestamp("9999-12-31T23:59:59-23:59", "stamp")

    def test_cli_reports_normalization_overflow_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "presence.json").write_text("[]\n", encoding="utf-8")
            (root / "lastseen.json").write_text("[]\n", encoding="utf-8")
            (root / "claims.json").write_text('{"claims":[]}\n', encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = main([
                    "--root", str(root),
                    "--observed-at", "0001-01-01T00:00:00+23:59",
                    "--source-commit", "a" * 40,
                ])
        self.assertEqual(status, 2)
        self.assertIn("observed_at must be RFC3339", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_blank_unknown_and_leap_second_contracts_remain(self) -> None:
        self.assertIsNone(_timestamp("", "stamp", allow_blank=True))
        self.assertEqual(
            _timestamp("2016-12-31T15:59:60-08:00", "stamp"),
            dt.datetime(2017, 1, 1, tzinfo=UTC),
        )

    def test_concurrent_raw_source_padding_fix_remains(self) -> None:
        raw = " 2026-09-01T15:00:00Z"
        with self.assertRaisesRegex(AgentLivenessError, r"lastseen\[actor\]\.ts must be RFC3339"):
            build_index(
                presence=[{"from": "actor", "presence": "PRESENT", "id": "r1", "ts": raw}],
                lastseen=[{"from": "actor", "id": "r1", "ts": raw, "to": "TABLE"}],
                claims={"claims": []},
                observed_at="2026-09-01T16:00:00Z",
                source_commit="a" * 40,
                source_blobs=BLOBS,
            )


if __name__ == "__main__":
    unittest.main()
