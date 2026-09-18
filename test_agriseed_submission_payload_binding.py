#!/usr/bin/env python3
"""Focused BD03 regressions for AgriSeed submission payload identity."""

from __future__ import annotations

from copy import deepcopy
import unittest

import agriseed_rush_work_allocator as gate


class AgriSeedSubmissionPayloadBindingTests(unittest.TestCase):
    def _valid_rows(self) -> list[dict]:
        return [
            deepcopy(row)
            for row in gate.build_acceptance_fixture()
            if row["expected_state"] == "ACCESSIONED"
        ]

    def test_source_hash_is_recomputed_and_exact_replay_is_no_mutation(self) -> None:
        row = self._valid_rows()[0]
        row["source_sha256"] = "0" * 64
        seen_bags: set[str] = set()
        seen_submissions: dict[str, str] = {}

        first = gate.evaluate_row(row, seen_bags, seen_submissions)
        expected = gate.sha256_hex(gate._source_payload(row))
        self.assertEqual(first["state"], "ACCESSIONED")
        self.assertEqual(first["source_sha256"], expected)
        self.assertNotEqual(first["source_sha256"], row["source_sha256"])
        self.assertEqual(seen_submissions[row["submission_id"]], expected)

        bags_before = set(seen_bags)
        submissions_before = dict(seen_submissions)
        replay = gate.evaluate_row(deepcopy(row), seen_bags, seen_submissions)
        self.assertEqual(replay["state"], "IDEMPOTENT_REPLAY")
        self.assertEqual(replay["source_sha256"], expected)
        self.assertEqual(seen_bags, bags_before)
        self.assertEqual(seen_submissions, submissions_before)

    def test_changed_payload_same_submission_fails_before_state_mutation(self) -> None:
        first_row, changed_row = self._valid_rows()[:2]
        changed_row["submission_id"] = first_row["submission_id"]
        # Preserve the stale caller digest from the first row.  The repair must
        # recompute the canonical payload rather than trusting this field.
        changed_row["source_sha256"] = first_row["source_sha256"]

        seen_bags: set[str] = set()
        seen_submissions: dict[str, str] = {}
        gate.evaluate_row(first_row, seen_bags, seen_submissions)
        bags_before = set(seen_bags)
        submissions_before = dict(seen_submissions)

        changed_digest = gate.sha256_hex(gate._source_payload(changed_row))
        self.assertNotEqual(
            changed_digest,
            seen_submissions[first_row["submission_id"]],
        )
        with self.assertRaisesRegex(ValueError, "^SUBMISSION_ID_PAYLOAD_MISMATCH$"):
            gate.evaluate_row(changed_row, seen_bags, seen_submissions)

        self.assertEqual(seen_bags, bags_before)
        self.assertEqual(seen_submissions, submissions_before)

    def test_hold_does_not_claim_submission_identity(self) -> None:
        held = next(
            deepcopy(row)
            for row in gate.build_acceptance_fixture()
            if row["expected_reason"] == "MISSING_BILLING"
        )
        seen_bags: set[str] = set()
        seen_submissions: dict[str, str] = {}

        first = gate.evaluate_row(held, seen_bags, seen_submissions)
        self.assertEqual(first["state"], "HELD")
        self.assertEqual(first["reason"], "MISSING_BILLING")
        self.assertNotIn(held["submission_id"], seen_submissions)
        self.assertEqual(seen_bags, set())

        # Preserve BD04's separate held->corrected boundary: a submission that
        # never accessioned is not retroactively bound by this BD03 repair.
        corrected = deepcopy(held)
        corrected["billing_account"] = "BILL-AST-CORRECTED"
        corrected["source_sha256"] = "stale-caller-digest"
        second = gate.evaluate_row(corrected, seen_bags, seen_submissions)
        self.assertEqual(second["state"], "ACCESSIONED")
        self.assertEqual(
            seen_submissions[corrected["submission_id"]],
            gate.sha256_hex(gate._source_payload(corrected)),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
