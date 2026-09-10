# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from pareto_rank import (
    CustodyError,
    FundingCandidate,
    POSTIMAGE,
    PREIMAGE,
    choose,
    git_blob_id,
    model_witness,
    patch_source,
    verify_source,
)


def synthetic_source() -> bytes:
    return b"before\n" + PREIMAGE + b"after\n"


class GitObjectContracts(unittest.TestCase):
    def test_git_blob_known_vector(self):
        self.assertEqual(
            git_blob_id(b"test content\n"),
            "d670460b4b4aece5915caf5c68d12f560a9fe3e4",
        )

    def test_exact_synthetic_source_can_be_verified_with_own_blob(self):
        data = synthetic_source()
        receipt = verify_source(data, expected_blob=git_blob_id(data))
        self.assertEqual(receipt["preimage_count"], 1)
        self.assertEqual(receipt["postimage_count"], 0)

    def test_wrong_source_blob_fails_closed(self):
        with self.assertRaisesRegex(CustodyError, "Git blob mismatch"):
            verify_source(synthetic_source(), expected_blob="0" * 40)

    def test_missing_preimage_fails_closed(self):
        data = b"before\nafter\n"
        with self.assertRaisesRegex(CustodyError, "preimage custody"):
            verify_source(data, expected_blob=git_blob_id(data))

    def test_duplicate_preimage_fails_closed(self):
        data = PREIMAGE + PREIMAGE
        with self.assertRaisesRegex(CustodyError, "preimage custody"):
            verify_source(data, expected_blob=git_blob_id(data))

    def test_already_patched_source_fails_closed(self):
        data = b"before\n" + POSTIMAGE + b"after\n"
        with self.assertRaisesRegex(CustodyError, "preimage custody"):
            verify_source(data, expected_blob=git_blob_id(data))


class PatchContracts(unittest.TestCase):
    def test_patch_changes_exactly_one_line_and_one_sign(self):
        data = synthetic_source()
        patched, receipt = patch_source(data, expected_blob=git_blob_id(data))
        self.assertEqual(receipt["changed_lines"], [2])
        self.assertEqual(patched.count(PREIMAGE), 0)
        self.assertEqual(patched.count(POSTIMAGE), 1)
        self.assertEqual(len(data), len(patched) - 1)  # one added minus sign
        self.assertEqual(patched.replace(POSTIMAGE, PREIMAGE, 1), data)

    def test_patch_is_deterministic(self):
        data = synthetic_source()
        first = patch_source(data, expected_blob=git_blob_id(data))
        second = patch_source(data, expected_blob=git_blob_id(data))
        self.assertEqual(first, second)

    def test_patch_receipt_hashes_output(self):
        data = synthetic_source()
        patched, receipt = patch_source(data, expected_blob=git_blob_id(data))
        self.assertEqual(receipt["candidate"]["sha256"], hashlib.sha256(patched).hexdigest())
        self.assertEqual(receipt["candidate"]["git_blob"], git_blob_id(patched))


class RankingContracts(unittest.TestCase):
    def setUp(self):
        self.low = FundingCandidate(1, 25, 1, 1, "CARROT")
        self.high = FundingCandidate(1, 190, 2, 1, "WOOL")

    def test_predecessor_selects_lower_cash(self):
        self.assertEqual(choose((self.low, self.high), repaired=False), self.low)

    def test_candidate_selects_higher_cash_at_equal_minimum_movement(self):
        self.assertEqual(choose((self.low, self.high), repaired=True), self.high)

    def test_movement_remains_primary(self):
        more_cash_but_more_movement = FundingCandidate(2, 10000, 1, 1, "MELON")
        self.assertEqual(
            choose((self.low, more_cash_but_more_movement), repaired=True),
            self.low,
        )

    def test_existing_deterministic_ties_are_preserved(self):
        a = FundingCandidate(1, 100, 1, 1, "CARROT")
        b = FundingCandidate(1, 100, 2, 1, "WOOL")
        self.assertEqual(choose((a, b), repaired=False), a)
        self.assertEqual(choose((a, b), repaired=True), a)

    def test_successor_maximizes_cash_within_minimum_movement_frontier(self):
        candidates = [
            FundingCandidate(moved, cash, source, 1, item)
            for moved in (1, 2, 3)
            for cash, source, item in ((5, 3, "EGG"), (90, 2, "MILK"), (40, 1, "WOOL"))
        ]
        chosen = choose(candidates, repaired=True)
        frontier = [candidate for candidate in candidates if candidate.moved == 1]
        self.assertEqual(chosen.remaining_cash, max(candidate.remaining_cash for candidate in frontier))

    def test_reduced_witness_is_strict_and_invariant_preserving(self):
        witness = model_witness()
        self.assertEqual(witness["predecessor"]["item"], "CARROT")
        self.assertEqual(witness["candidate"]["item"], "WOOL")
        self.assertEqual(witness["certified_remaining_cash_delta"], 165)
        self.assertTrue(witness["invariants"]["minimum_moved_units_equal"])
        self.assertTrue(witness["invariants"]["same_fixed_acquisition_completed"])
        self.assertTrue(witness["invariants"]["sale_quantities_preserved_by_item"])


if __name__ == "__main__":
    unittest.main()
