#!/usr/bin/env python3
"""Regression for bound AgriSeed submission identity taking precedence over HOLDs."""

from __future__ import annotations

from copy import deepcopy
import unittest

import agriseed_rush_work_allocator as gate


class AgriSeedBoundSubmissionPrecedenceTests(unittest.TestCase):
    def _valid_row(self) -> dict:
        return deepcopy(
            next(
                row
                for row in gate.build_acceptance_fixture()
                if row["expected_state"] == "ACCESSIONED"
            )
        )

    def test_bound_submission_changed_to_missing_billing_mismatches_before_hold(self) -> None:
        row = self._valid_row()
        seen_bags: set[str] = set()
        seen_submissions: dict[str, str] = {}

        first = gate.evaluate_row(row, seen_bags, seen_submissions)
        self.assertEqual(first["state"], "ACCESSIONED")
        bags_before = set(seen_bags)
        submissions_before = dict(seen_submissions)

        changed = deepcopy(row)
        changed["billing_account"] = ""
        # Deliberately retain the stale caller digest: identity authority is the
        # freshly recomputed effective payload, not this caller-provided field.
        changed["source_sha256"] = row["source_sha256"]

        with self.assertRaisesRegex(ValueError, "^SUBMISSION_ID_PAYLOAD_MISMATCH$"):
            gate.evaluate_row(changed, seen_bags, seen_submissions)

        self.assertEqual(seen_bags, bags_before)
        self.assertEqual(seen_submissions, submissions_before)

    def test_first_seen_missing_billing_keeps_existing_hold_semantics(self) -> None:
        row = self._valid_row()
        row["submission_id"] = "AST-FIRST-SEEN-MISSING-BILLING"
        row["billing_account"] = ""
        row["source_sha256"] = "stale-caller-digest"
        seen_bags: set[str] = set()
        seen_submissions: dict[str, str] = {}

        outcome = gate.evaluate_row(row, seen_bags, seen_submissions)
        self.assertEqual(outcome["state"], "HELD")
        self.assertEqual(outcome["reason"], "MISSING_BILLING")
        self.assertEqual(seen_bags, set())
        self.assertEqual(seen_submissions, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
