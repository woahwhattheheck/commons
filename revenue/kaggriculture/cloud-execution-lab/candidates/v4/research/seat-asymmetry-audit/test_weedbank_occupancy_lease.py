import inspect
import unittest

import weedbank_occupancy_lease as W


class WeedbankOccupancyLeaseTests(unittest.TestCase):
    def base(self, **overrides):
        args = dict(
            current_tile=None,
            structure_kind="COOP",
            structure_will_remain_empty=True,
            build_reachable=True,
            dig_reachable=True,
            dig_reserved_before_reuse=True,
            tile_needed_before_dig=False,
            occupied_eods=30,
            weed_spawn_chance=0.005,
            weed_clear_action_cost=1,
            route_action_cost_per_weed=0,
            build_action_opportunity_cost=0,
            dig_action_opportunity_cost=1,
            temporary_tile_opportunity_cost=0,
        )
        args.update(overrides)
        return args

    def test_default_weed_only_lease_is_dominated(self):
        result = W.occupancy_lease_gate(**self.base())
        self.assertFalse(result["admitted"])
        self.assertAlmostEqual(result["expected_weed_events_avoided"], 0.15)
        self.assertAlmostEqual(result["expected_action_margin"], -0.85)

    def test_expensive_route_can_make_lease_positive(self):
        result = W.occupancy_lease_gate(
            **self.base(route_action_cost_per_weed=10)
        )
        self.assertTrue(result["admitted"])
        self.assertAlmostEqual(result["expected_action_benefit"], 1.65)
        self.assertAlmostEqual(result["expected_action_margin"], 0.65)

    def test_nonempty_tile_refused(self):
        result = W.occupancy_lease_gate(
            **self.base(current_tile={"kind": "WEED"})
        )
        self.assertEqual(result["reason"], "tile-not-empty")

    def test_structure_must_stay_empty(self):
        result = W.occupancy_lease_gate(
            **self.base(structure_will_remain_empty=False)
        )
        self.assertEqual(result["reason"], "structure-not-empty-lease")

    def test_reclamation_obligation_required(self):
        result = W.occupancy_lease_gate(
            **self.base(dig_reserved_before_reuse=False)
        )
        self.assertEqual(result["reason"], "no-reclamation-obligation")

    def test_tile_reuse_conflict_refused(self):
        result = W.occupancy_lease_gate(
            **self.base(tile_needed_before_dig=True)
        )
        self.assertEqual(result["reason"], "tile-needed-before-reclamation")

    def test_no_hidden_seed_surface(self):
        self.assertNotIn("seed", inspect.signature(W.occupancy_lease_gate).parameters)
        self.assertFalse(
            W.occupancy_lease_gate(**self.base())["hidden_seed_targeting_allowed"]
        )

    def test_bool_cost_refused(self):
        result = W.occupancy_lease_gate(
            **self.base(dig_action_opportunity_cost=True)
        )
        self.assertEqual(result["reason"], "malformed-economics")

    def test_environment_divergence_gate(self):
        self.assertEqual(
            W.environment_path_classification(
                baseline_unlocked_shops=["PIZZA_SHOP"],
                candidate_unlocked_shops=["BRUNCH_SPOT"],
                baseline_total_empty_tiles=50,
                candidate_total_empty_tiles=49,
            ),
            W.ENVIRONMENT_PATH_DIVERGED,
        )

    def test_same_total_empty_is_negative_control(self):
        self.assertEqual(
            W.environment_path_classification(
                baseline_unlocked_shops=["PIZZA_SHOP"],
                candidate_unlocked_shops=["PIZZA_SHOP"],
                baseline_total_empty_tiles=50,
                candidate_total_empty_tiles=50,
            ),
            W.RNG_CURSOR_NEUTRAL_CONTROL,
        )

    def test_cursor_exposure_without_shop_flip_is_not_divergence(self):
        self.assertEqual(
            W.environment_path_classification(
                baseline_unlocked_shops=["PIZZA_SHOP"],
                candidate_unlocked_shops=["PIZZA_SHOP"],
                baseline_total_empty_tiles=50,
                candidate_total_empty_tiles=49,
            ),
            W.RNG_CURSOR_EXPOSED_NO_DIVERGENCE,
        )

    def test_same_empty_but_shop_flip_is_unexplained(self):
        self.assertEqual(
            W.environment_path_classification(
                baseline_unlocked_shops=["PIZZA_SHOP"],
                candidate_unlocked_shops=["BRUNCH_SPOT"],
                baseline_total_empty_tiles=50,
                candidate_total_empty_tiles=50,
            ),
            W.UNEXPLAINED_ENVIRONMENT_DIVERGENCE,
        )

    def test_expected_events_input_validation(self):
        self.assertEqual(W.daily_clear_expected_weed_events_avoided(30), 0.15)
        self.assertIsNone(W.daily_clear_expected_weed_events_avoided(True))
        self.assertIsNone(W.daily_clear_expected_weed_events_avoided(30, 1.1))


if __name__ == "__main__":
    unittest.main()
