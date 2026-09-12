# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path
import unittest

from weedbank_occupancy_lease import (
    ENGINE_GIT_BLOB,
    WeedbankContractError,
    expected_empty_tile_rng_draws,
    git_blob_sha1,
    occupancy_lease_receipt,
    verify_engine_bytes,
    weed_spawn_probability,
)


class WeedbankOccupancyLeaseTests(unittest.TestCase):
    def test_exact_pinned_engine_and_semantic_anchors(self):
        lab = Path(__file__).resolve().parents[4]
        engine = lab / "reference" / "engine" / "kaggriculture.py"
        data = engine.read_bytes()
        self.assertEqual(git_blob_sha1(data), ENGINE_GIT_BLOB)
        self.assertTrue(verify_engine_bytes(data))

    def test_standard_thirty_eod_direct_labor_is_negative(self):
        receipt = occupancy_lease_receipt(30, 0.005, restore_with_dig=True)
        self.assertAlmostEqual(receipt["weed_spawn_probability"], 0.13961580808530394)
        self.assertAlmostEqual(receipt["expected_rng_draws_suppressed"], 27.92316161706079)
        self.assertAlmostEqual(receipt["direct_action_delta"], -1.860384191914696)
        self.assertFalse(receipt["direct_weed_labor_advantage"])

    def test_even_nonrestored_carpet_has_no_direct_labor_edge(self):
        receipt = occupancy_lease_receipt(30, 0.005, restore_with_dig=False)
        self.assertAlmostEqual(receipt["direct_action_delta"], -0.8603841919146961)
        self.assertFalse(receipt["direct_weed_labor_advantage"])

    def test_baseline_cleanup_is_bounded_by_one_action(self):
        for eods in (0, 1, 30, 1000):
            probability = weed_spawn_probability(eods, 0.005)
            self.assertGreaterEqual(probability, 0.0)
            self.assertLessEqual(probability, 1.0)

    def test_zero_weed_chance_still_moves_rng_cursor(self):
        receipt = occupancy_lease_receipt(30, 0.0)
        self.assertEqual(receipt["weed_spawn_probability"], 0.0)
        self.assertEqual(receipt["expected_rng_draws_suppressed"], 30.0)
        self.assertEqual(receipt["direct_action_delta"], -2.0)

    def test_certain_weed_consumes_only_first_empty_tile_draw(self):
        self.assertEqual(weed_spawn_probability(30, 1.0), 1.0)
        self.assertEqual(expected_empty_tile_rng_draws(30, 1.0), 1.0)

    def test_zero_horizon(self):
        receipt = occupancy_lease_receipt(0, 0.005)
        self.assertEqual(receipt["weed_spawn_probability"], 0.0)
        self.assertEqual(receipt["expected_rng_draws_suppressed"], 0.0)
        self.assertEqual(receipt["direct_action_delta"], -2.0)

    def test_no_runtime_or_hidden_seed_authority(self):
        receipt = occupancy_lease_receipt(30)
        self.assertFalse(receipt["rng_decision_authority"])
        self.assertFalse(receipt["hidden_seed_targeting_authority"])
        self.assertFalse(receipt["runtime_policy_authority"])

    def test_type_and_range_poison_fail_closed(self):
        for value in (-1, True, 1.5, "30"):
            with self.assertRaises(WeedbankContractError):
                occupancy_lease_receipt(value)  # type: ignore[arg-type]
        for value in (-0.1, 1.1, True, float("nan"), float("inf"), "0.005"):
            with self.assertRaises(WeedbankContractError):
                occupancy_lease_receipt(30, value)  # type: ignore[arg-type]
        with self.assertRaises(WeedbankContractError):
            occupancy_lease_receipt(30, restore_with_dig=1)  # type: ignore[arg-type]

    def test_source_drift_rejected(self):
        with self.assertRaises(WeedbankContractError):
            verify_engine_bytes(b"not the engine")


if __name__ == "__main__":
    unittest.main()
