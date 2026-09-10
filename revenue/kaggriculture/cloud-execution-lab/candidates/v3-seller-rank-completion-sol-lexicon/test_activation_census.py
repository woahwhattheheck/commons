# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import unittest

import activation_census


class ActivationCensusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = activation_census.build_census()

    def test_declared_grid_has_exact_pair_counts(self):
        self.assertEqual(
            self.value["totals"],
            {
                "aggregate_discriminated": 1382,
                "aggregate_equal": 66,
                "eligible_pairs": 18189,
                "pairwise_choice_changes": 587,
                "primary_ties": 1448,
            },
        )

    def test_most_primary_ties_have_omitted_discriminator(self):
        self.assertGreater(
            self.value["aggregate_discrimination_rate_given_primary_tie"], 0.95
        )
        self.assertGreater(
            self.value["pairwise_choice_change_rate_given_primary_tie"], 0.40
        )

    def test_census_is_explicitly_not_strength_or_frequency_evidence(self):
        interpretation = self.value["interpretation"]
        self.assertIn("do not estimate live trajectory frequency", interpretation)
        self.assertIn("do not", interpretation)
        self.assertIn("episode-level score gain", interpretation)


if __name__ == "__main__":
    unittest.main(verbosity=2)
