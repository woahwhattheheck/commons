#!/usr/bin/env python3
"""Focused tests for immutable first-seen row/payload identity binding."""
from __future__ import annotations

from copy import deepcopy
import unittest

from host import payload_binding as binding


class PayloadBindingTests(unittest.TestCase):
    def test_first_seen_binds_then_exact_replay_is_a_noop(self):
        bindings = {}
        payload = {"sample": "A-17", "value": 2.5, "flags": ["ok", True]}

        self.assertEqual(binding.bind_first_seen_payload(bindings, "ROW-001", payload), binding.BOUND)
        frozen = deepcopy(bindings)
        self.assertEqual(binding.bind_first_seen_payload(bindings, "ROW-001", payload), binding.REPLAY_NOOP)
        self.assertEqual(bindings, frozen)

    def test_key_order_does_not_change_payload_identity(self):
        bindings = {}
        first = {"sample": "A-17", "result": {"unit": "mg/L", "value": 2}}
        reordered = {"result": {"value": 2, "unit": "mg/L"}, "sample": "A-17"}

        binding.bind_first_seen_payload(bindings, "ROW-002", first)
        self.assertEqual(binding.bind_first_seen_payload(bindings, "ROW-002", reordered), binding.REPLAY_NOOP)

    def test_changed_payload_same_id_fails_before_any_journal_mutation(self):
        journal = {"row_payload_sha256": {}, "events": [], "jobs": []}
        binding.bind_first_seen_payload(journal["row_payload_sha256"], "ROW-003", {"value": 7, "unit": "mg/L"})
        before = deepcopy(journal)

        with self.assertRaises(binding.PayloadBindingMismatch):
            binding.bind_first_seen_payload(
                journal["row_payload_sha256"],
                "ROW-003",
                {"value": 8, "unit": "mg/L"},
            )

        self.assertEqual(journal, before)

    def test_invalid_id_payload_and_stored_state_fail_without_mutation(self):
        cases = [
            ("", {"value": 1}),
            ("   ", {"value": 1}),
            (7, {"value": 1}),
            ("ROW-004", ["not", "an", "object"]),
            ("ROW-004", {"value": float("inf")}),
            ("ROW-004", {1: "non-string-key"}),
            ("ROW-004", {"value": ("tuple",)}),
        ]
        for row_id, payload in cases:
            with self.subTest(row_id=row_id, payload=payload):
                bindings = {}
                before = deepcopy(bindings)
                with self.assertRaises(binding.PayloadBindingError):
                    binding.bind_first_seen_payload(bindings, row_id, payload)
                self.assertEqual(bindings, before)

        bindings = {"ROW-005": "not-a-digest"}
        before = deepcopy(bindings)
        with self.assertRaises(binding.PayloadBindingError):
            binding.bind_first_seen_payload(bindings, "ROW-005", {"value": 1})
        self.assertEqual(bindings, before)

    def test_canonical_hash_is_stable_and_payload_sensitive(self):
        a = {"name": "café", "nested": [{"x": 1}, None]}
        b = {"nested": [{"x": 1}, None], "name": "café"}
        c = {"nested": [{"x": 2}, None], "name": "café"}

        self.assertEqual(binding.canonical_payload_sha256(a), binding.canonical_payload_sha256(b))
        self.assertNotEqual(binding.canonical_payload_sha256(a), binding.canonical_payload_sha256(c))


if __name__ == "__main__":
    unittest.main()
