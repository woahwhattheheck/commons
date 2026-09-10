# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import unittest

import holdout_admission as holdout


class HoldoutCustodyTests(unittest.TestCase):
    def test_seed_derivation_is_exact_and_disjoint(self) -> None:
        self.assertEqual(holdout.derive_seeds(), holdout.HOLDOUT_SEEDS)
        self.assertEqual(
            set(holdout.HOLDOUT_SEEDS) & set(holdout.DEVELOPMENT_SEEDS),
            set(),
        )
        self.assertEqual(len(set(holdout.HOLDOUT_SEEDS)), 8)

    def test_literal_grid_is_six_opponents_by_eight_seeds_by_both_seats(self) -> None:
        parent = holdout.load_parent()
        self.assertEqual(parent.OPPONENTS, holdout.HOLDOUT_OPPONENTS)
        self.assertEqual(parent.SEEDS, holdout.HOLDOUT_SEEDS)
        self.assertEqual(len(parent.expected_keys()), 6 * 8 * 2)

    def test_metadata_spends_exactly_one_hypothesis(self) -> None:
        metadata = holdout.holdout_metadata()
        self.assertEqual(metadata["candidate_hypotheses_spent"], 1)
        self.assertEqual(metadata["development_seed_overlap"], [])
        self.assertEqual(metadata["paired_cells_per_arm"], 96)
        self.assertTrue(
            metadata["economic_result_may_not_be_tuned_on_this_bank"]
        )

    def test_opponent_order_is_precommitted(self) -> None:
        self.assertEqual(
            holdout.HOLDOUT_OPPONENTS,
            ("apex", "kaito_v43", "cok_v10", "public_bt12", "v1", "v2"),
        )


if __name__ == "__main__":
    unittest.main()
