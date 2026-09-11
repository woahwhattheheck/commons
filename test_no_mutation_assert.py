#!/usr/bin/env python3
"""Focused tests for denied-operation no-mutation assertions."""
from __future__ import annotations

import unittest

from host.no_mutation_assert import (
    NoMutationAssertionError,
    NoMutationStateError,
    assert_raises_without_mutation,
    snapshot_json_state,
)


class NoMutationAssertTests(unittest.TestCase):
    def test_expected_denial_returns_exception_and_preserves_state(self):
        state = {"events": [], "journal": {"status": "HOLD", "retries": 0}}
        before = snapshot_json_state(state)

        def deny():
            raise ValueError("DENIED_BAD_INPUT")

        exc = assert_raises_without_mutation(state, deny, ValueError)
        self.assertEqual("DENIED_BAD_INPUT", str(exc))
        self.assertEqual(before, snapshot_json_state(state))

    def test_mutation_before_expected_raise_is_detected(self):
        state = {"events": [], "journal": {"status": "HOLD"}}

        def mutate_then_deny():
            state["events"].append({"kind": "should-not-exist"})
            raise ValueError("DENIED")

        with self.assertRaisesRegex(NoMutationAssertionError, "state mutated before expected ValueError"):
            assert_raises_without_mutation(state, mutate_then_deny, ValueError)

    def test_nested_and_order_mutations_are_detected(self):
        nested = {"items": [{"value": 1}], "events": []}

        def mutate_nested():
            nested["items"][0]["value"] = 2
            raise RuntimeError("x")

        reordered = {"queue": ["A", "B", "C"]}

        def mutate_order():
            reordered["queue"].reverse()
            raise RuntimeError("x")

        for state, operation in ((nested, mutate_nested), (reordered, mutate_order)):
            with self.subTest(state=state):
                with self.assertRaisesRegex(NoMutationAssertionError, "state mutated"):
                    assert_raises_without_mutation(state, operation, RuntimeError)

    def test_missing_or_unexpected_exception_fails_the_assertion(self):
        state = {"events": []}
        with self.assertRaisesRegex(NoMutationAssertionError, "did not raise ValueError"):
            assert_raises_without_mutation(state, lambda: None, ValueError)

        with self.assertRaisesRegex(NoMutationAssertionError, "unexpected KeyError"):
            assert_raises_without_mutation(state, lambda: (_ for _ in ()).throw(KeyError("wrong")), ValueError)

    def test_state_becoming_non_json_is_detected(self):
        state = {"events": []}

        def corrupt_then_deny():
            state["events"].append(float("nan"))
            raise ValueError("DENIED")

        with self.assertRaisesRegex(NoMutationAssertionError, "state became invalid"):
            assert_raises_without_mutation(state, corrupt_then_deny, ValueError)

    def test_invalid_initial_state_fails_before_operation_runs(self):
        state = {"events": [float("inf")]}
        ran = {"value": False}

        def operation():
            ran["value"] = True
            raise ValueError("DENIED")

        with self.assertRaisesRegex(NoMutationStateError, "non-finite"):
            assert_raises_without_mutation(state, operation, ValueError)
        self.assertFalse(ran["value"])


if __name__ == "__main__":
    unittest.main()
