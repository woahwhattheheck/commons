#!/usr/bin/env python3
from __future__ import annotations

import math
import unittest

from host.no_mutation import (
    SnapshotError,
    assert_json_unchanged,
    assert_raises_without_mutation,
    snapshot_json,
)


class Denied(ValueError):
    pass


class NoMutationTests(unittest.TestCase):
    def test_snapshot_is_canonical_across_object_insertion_order(self):
        left = {"b": [2, 3], "a": {"x": True}}
        right = {"a": {"x": True}, "b": [2, 3]}
        self.assertEqual(snapshot_json(left), snapshot_json(right))

    def test_expected_denial_without_mutation_returns_exception(self):
        journal = {"events": [], "jobs": {"J1": {"status": "READY"}}}

        def deny():
            raise Denied("invalid transition")

        caught = assert_raises_without_mutation(Denied, deny, journal, label="journal")
        self.assertIsInstance(caught, Denied)
        self.assertEqual(journal["events"], [])

    def test_nested_mutation_is_detected_even_with_expected_exception(self):
        journal = {"events": [], "jobs": {"J1": {"status": "READY"}}}

        def corrupt_then_deny():
            journal["jobs"]["J1"]["status"] = "RELEASED"
            raise Denied("blocked too late")

        with self.assertRaisesRegex(AssertionError, r"journal\[0\] mutated"):
            assert_raises_without_mutation(Denied, corrupt_then_deny, journal, label="journal")

    def test_multiple_states_report_the_mutated_state_index(self):
        journal = {"events": []}
        cache = {"seen": []}

        def corrupt_cache_then_deny():
            cache["seen"].append("row-1")
            raise Denied("duplicate")

        with self.assertRaisesRegex(AssertionError, r"state\[1\] mutated"):
            assert_raises_without_mutation(Denied, corrupt_cache_then_deny, journal, cache)

    def test_post_state_becoming_non_json_is_mutation_failure(self):
        journal = {"value": 1.0}

        def corrupt_then_deny():
            journal["value"] = math.inf
            raise Denied("bad value")

        with self.assertRaisesRegex(AssertionError, r"state\[0\] is no longer strict JSON"):
            assert_raises_without_mutation(Denied, corrupt_then_deny, journal)

    def test_wrong_exception_is_reported_after_no_mutation_check(self):
        journal = {"events": []}

        def wrong_error():
            raise RuntimeError("unexpected")

        with self.assertRaisesRegex(AssertionError, r"RuntimeError, expected Denied") as caught:
            assert_raises_without_mutation(Denied, wrong_error, journal)
        self.assertIsInstance(caught.exception.__cause__, RuntimeError)

    def test_no_exception_is_reported_when_state_is_unchanged(self):
        journal = {"events": []}
        with self.assertRaisesRegex(AssertionError, r"did not raise Denied"):
            assert_raises_without_mutation(Denied, lambda: None, journal)

    def test_invalid_pre_state_fails_before_operation_runs(self):
        calls = []
        journal = {"bad": math.nan}

        with self.assertRaises(SnapshotError):
            assert_raises_without_mutation(Denied, lambda: calls.append("ran"), journal)
        self.assertEqual(calls, [])

    def test_non_string_key_fails_before_operation_runs(self):
        calls = []
        journal = {1: "not strict JSON"}

        with self.assertRaisesRegex(SnapshotError, r"object keys must be strings"):
            assert_raises_without_mutation(Denied, lambda: calls.append("ran"), journal)
        self.assertEqual(calls, [])

    def test_direct_snapshot_assertion_detects_change(self):
        state = {"items": [1, 2]}
        before = snapshot_json(state)
        assert_json_unchanged(before, state, label="ledger")
        state["items"].append(3)
        with self.assertRaisesRegex(AssertionError, r"ledger mutated"):
            assert_json_unchanged(before, state, label="ledger")

    def test_cycles_fail_closed(self):
        state = []
        state.append(state)
        with self.assertRaisesRegex(SnapshotError, r"cyclic containers"):
            snapshot_json(state)


if __name__ == "__main__":
    unittest.main()
