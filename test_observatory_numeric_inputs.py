"""Regressions for numeric JSON inputs to Observatory's read-only views."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from host.observatory import freshness, read_observatory, select_snapshot


BAKED_AT = "2026-09-01T00:00:00Z"
CHECKED_AT = "2026-09-06T00:00:00Z"


def baked_snapshot():
    return {
        "schema": "commons-observatory/v0.1",
        "protocol": "commons-protocol/v0.1",
        "now": BAKED_AT,
        "stale_after_seconds": 600,
        "digest": "unchanged-bake-digest",
        "open_door": True,
        "sessions": [{"session_id": str(i)} for i in range(5)],
        "timeline": [{"id": str(i)} for i in range(3)],
        "presence": [{"claim": "FLINT"}],
    }


class ObservatoryNumericInputTests(unittest.TestCase):
    def setUp(self):
        self.snap = baked_snapshot()

    def select(self, arguments):
        return select_snapshot(self.snap, arguments, now=CHECKED_AT)

    def test_overflowing_json_offset_defaults_to_zero(self):
        for literal in ("1e309", "-1e309"):
            with self.subTest(literal=literal):
                result = self.select(json.loads('{"offset": ' + literal + ', "limit": 2}'))
                self.assertEqual(result["sessions"], self.snap["sessions"][:2])
                self.assertEqual(result["pagination"][0]["offset"], 0)
                self.assertEqual(result["pagination"][0]["next_cursor"], "2")

    def test_overflowing_json_cursor_defaults_to_zero(self):
        for literal in ("1e309", "-1e309"):
            for offset in (None, ""):
                with self.subTest(literal=literal, offset=offset):
                    arguments = json.loads('{"cursor": ' + literal + ', "limit": 2}')
                    arguments["offset"] = offset
                    result = self.select(arguments)
                    self.assertEqual(result["sessions"], self.snap["sessions"][:2])
                    self.assertEqual(result["pagination"][0]["offset"], 0)

    def test_overflowing_json_limit_preserves_unbounded_default(self):
        for literal in ("1e309", "-1e309"):
            with self.subTest(literal=literal):
                result = self.select(json.loads('{"offset": 1, "limit": ' + literal + '}'))
                self.assertEqual(result["sessions"], self.snap["sessions"][1:])
                self.assertIsNone(result["pagination"][0]["limit"])
                self.assertIsNone(result["pagination"][0]["next_cursor"])

    def test_existing_invalid_pagination_defaults_are_unchanged(self):
        for value in (None, "", "bad", [], {}, -1, float("nan")):
            with self.subTest(value=value):
                result = self.select({"offset": value, "limit": value})
                self.assertEqual(result["sessions"], self.snap["sessions"])
                self.assertEqual(result["pagination"][0]["offset"], 0)
                self.assertIsNone(result["pagination"][0]["limit"])

    def test_explicit_offset_precedes_cursor(self):
        result = self.select({"offset": 0, "cursor": 3, "limit": 2})
        self.assertEqual(result["sessions"], self.snap["sessions"][:2])

    def test_numeric_string_cursor_and_limit_paginate(self):
        result = self.select({"cursor": "2", "limit": "2"})
        self.assertEqual(result["sessions"], self.snap["sessions"][2:4])
        self.assertEqual(result["pagination"][0]["next_cursor"], "4")
        final = self.select({"cursor": "4", "limit": "2"})
        self.assertEqual(final["sessions"], self.snap["sessions"][4:])
        self.assertIsNone(final["pagination"][0]["next_cursor"])

    def test_huge_integer_pagination_remains_supported(self):
        huge = 10 ** 400
        self.assertEqual(self.select({"offset": huge})["sessions"], [])
        self.assertEqual(self.select({"limit": huge})["sessions"], self.snap["sessions"])

    def test_census_overflow_does_not_mutate_bake_or_arguments(self):
        arguments = json.loads('{"view": "census", "offset": 1e309, "limit": 1}')
        original_snap = copy.deepcopy(self.snap)
        original_arguments = copy.deepcopy(arguments)
        result = self.select(arguments)
        self.assertEqual(self.snap, original_snap)
        self.assertEqual(arguments, original_arguments)
        self.assertEqual(result["sessions"], self.snap["sessions"][:1])
        self.assertEqual(result["presence"], self.snap["presence"])
        self.assertEqual(result["provenance"]["digest"], original_snap["digest"])
        self.assertEqual(result["freshness"]["snapshot_at"], BAKED_AT)
        self.assertIs(result["open_door"], True)

    def test_selection_preserves_explicit_coverage_note(self):
        self.snap["coverage_note"] = "Provider coverage is incomplete. Session counts are partial."
        result = self.select({})
        self.assertEqual(result["coverage_note"], self.snap["coverage_note"])

    def test_filesystem_bake_reader_handles_overflow(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "observatory.json"
            payload = json.dumps(self.snap) + "\n"
            path.write_text(payload, encoding="utf-8")
            result = read_observatory(root, json.loads('{"view": "timeline", "limit": 1e309}'))
            self.assertEqual(result["timeline"], self.snap["timeline"])
            self.assertEqual(result["provenance"]["source"], "observatory.json")
            self.assertEqual(path.read_text(encoding="utf-8"), payload)

    def test_nonfinite_freshness_threshold_is_unknown(self):
        for threshold in (json.loads("1e309"), json.loads("-1e309"), float("nan")):
            with self.subTest(threshold=threshold):
                self.snap["stale_after_seconds"] = threshold
                result = freshness(self.snap, CHECKED_AT)
                self.assertEqual(result["state"], "UNKNOWN")
                self.assertEqual(result["age_seconds"], 5 * 24 * 60 * 60)
                self.assertEqual(result["snapshot_at"], BAKED_AT)

    def test_finite_threshold_boundaries_are_unchanged(self):
        for threshold, state in ((0, "STALE"), (600.5, "STALE"), (432000, "FRESH"), (432000.5, "FRESH")):
            with self.subTest(threshold=threshold):
                self.snap["stale_after_seconds"] = threshold
                self.assertEqual(freshness(self.snap, CHECKED_AT)["state"], state)
        self.snap["stale_after_seconds"] = 0
        self.assertEqual(freshness(self.snap, BAKED_AT)["state"], "FRESH")

    def test_invalid_freshness_thresholds_stay_unknown(self):
        for threshold in (None, True, False, "600", -1, [], {}):
            with self.subTest(threshold=threshold):
                self.snap["stale_after_seconds"] = threshold
                self.assertEqual(freshness(self.snap, CHECKED_AT)["state"], "UNKNOWN")

    def test_huge_integer_threshold_does_not_require_float_conversion(self):
        self.snap["stale_after_seconds"] = 10 ** 400
        self.assertEqual(freshness(self.snap, CHECKED_AT)["state"], "FRESH")

    def test_invalid_or_future_bake_time_stays_unknown(self):
        for observed in (None, "not-a-date", "2027-01-01T00:00:00Z"):
            with self.subTest(observed=observed):
                self.snap["now"] = observed
                self.assertEqual(freshness(self.snap, CHECKED_AT)["state"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
