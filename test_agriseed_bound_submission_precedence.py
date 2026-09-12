#!/usr/bin/env python3
"""Regressions for AgriSeed bound-ID precedence and first-seen HOLD order."""

from __future__ import annotations

from copy import deepcopy
import unittest

import agriseed_rush_work_allocator as gate


class AgriSeedBoundSubmissionPrecedenceTests(unittest.TestCase):
    def _valid_rows(self) -> list[dict]:
        return [
            deepcopy(row)
            for row in gate.build_acceptance_fixture()
            if row["expected_state"] == "ACCESSIONED"
        ]

    def _valid_row(self) -> dict:
        return self._valid_rows()[0]

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

    def test_first_seen_duplicate_bag_precedes_malformed_duration(self) -> None:
        seed, row = self._valid_rows()[:2]
        seen_bags: set[str] = set()
        seen_submissions: dict[str, str] = {}
        first = gate.evaluate_row(seed, seen_bags, seen_submissions)
        self.assertEqual(first["state"], "ACCESSIONED")
        bags_before = set(seen_bags)
        submissions_before = dict(seen_submissions)

        row["submission_id"] = "AST-FIRST-SEEN-DUP-MALFORMED-DURATION"
        row["bag_barcode"] = seed["bag_barcode"]
        row["reported_duration_hours"] = "not-an-int"
        row["source_sha256"] = "stale-caller-digest"

        outcome = gate.evaluate_row(row, seen_bags, seen_submissions)
        self.assertEqual(outcome["state"], "HELD")
        self.assertEqual(outcome["reason"], "DUPLICATE_BAG_BARCODE")
        self.assertEqual(seen_bags, bags_before)
        self.assertEqual(seen_submissions, submissions_before)

    def test_first_seen_certificate_hold_precedes_malformed_duration(self) -> None:
        row = self._valid_rows()[1]
        row["submission_id"] = "AST-FIRST-SEEN-CERT-MALFORMED-DURATION"
        row["bag_barcode"] = "BAG-FIRST-SEEN-CERT-MALFORMED"
        row["certificate"] = "WRONG_CERT_NOT_ON_FILE"
        row["reported_duration_hours"] = "not-an-int"
        row["source_sha256"] = "stale-caller-digest"
        seen_bags: set[str] = set()
        seen_submissions: dict[str, str] = {}

        outcome = gate.evaluate_row(row, seen_bags, seen_submissions)
        self.assertEqual(outcome["state"], "HELD")
        self.assertEqual(outcome["reason"], "INVALID_RULE_CERTIFICATE")
        self.assertEqual(seen_bags, set())
        self.assertEqual(seen_submissions, {})

    def test_first_seen_duration_parse_keeps_preimage_precedence_over_analyst_hold(self) -> None:
        row = self._valid_row()
        row["submission_id"] = "AST-FIRST-SEEN-ANALYST-MALFORMED-DURATION"
        row["bag_barcode"] = "BAG-FIRST-SEEN-ANALYST-MALFORMED"
        row["analyst_id"] = "NOT-A-QUALIFIED-ANALYST"
        row["reported_duration_hours"] = "not-an-int"
        row["source_sha256"] = "stale-caller-digest"
        seen_bags: set[str] = set()
        seen_submissions: dict[str, str] = {}

        with self.assertRaises(ValueError):
            gate.evaluate_row(row, seen_bags, seen_submissions)

        self.assertEqual(seen_bags, set())
        self.assertEqual(seen_submissions, {})

    def test_failed_report_construction_does_not_bind_submission_or_bag(self) -> None:
        row = self._valid_row()
        row["submission_id"] = "AST-FIRST-SEEN-MALFORMED-INDEX"
        row["bag_barcode"] = "BAG-FIRST-SEEN-MALFORMED-INDEX"
        # Keep an explicit valid analyst so index conversion is not consumed by
        # fallback analyst selection; the failure occurs at accession-id build.
        self.assertIn(row["analyst_id"], gate.ANALYSTS)
        row["index"] = "not-an-int"
        row["source_sha256"] = "stale-caller-digest"
        seen_bags: set[str] = set()
        seen_submissions: dict[str, str] = {}

        with self.assertRaises(ValueError):
            gate.evaluate_row(row, seen_bags, seen_submissions)

        self.assertEqual(seen_bags, set())
        self.assertEqual(seen_submissions, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
