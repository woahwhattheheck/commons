import copy
import unittest

import liquidation_bound as L


def base_observation():
    return {
        "player": 0,
        "step": 600,
        "farms": [{
            "sale_counters": {"MELON": 0},
            "tiles": [[None for _ in range(4)] for _ in range(4)],
        }],
        "private": {
            "shed": {"MELON": 0},
            "inventories": [{}, {}],
        },
        "market": {"inventory": {"MELON": 10000}},
    }


class RealizationBoundTests(unittest.TestCase):
    def test_missing_certificate_is_exact_identity(self):
        props = [{"crop": "MELON", "tiles": list(range(8)), "seed_units": 8}]
        self.assertIs(L.filter_proposals_with_realization_bound(props, base_observation(), None), props)

    def test_bad_certificate_is_exact_identity(self):
        props = [{"crop": "MELON", "tiles": [0, 1]}]
        self.assertIs(L.filter_proposals_with_realization_bound(props, base_observation(), True), props)
        self.assertIs(L.filter_proposals_with_realization_bound(props, base_observation(), -1), props)

    def test_large_certificate_can_exceed_legacy_four_plant_cap(self):
        props = [{"crop": "MELON", "tiles": list(range(10)), "seed_units": 10}]
        out = L.filter_proposals_with_realization_bound(props, base_observation(), 60)
        self.assertIs(out, props)
        self.assertEqual(L.max_new_melon_plants(base_observation(), 60), 10)

    def test_outstanding_held_and_planted_supply_consumes_certificate(self):
        obs = base_observation()
        obs["private"]["shed"]["MELON"] = 12
        obs["farms"][0]["tiles"][0][0] = {"kind": "PLANT", "crop": "MELON"}
        obs["farms"][0]["tiles"][0][1] = {"kind": "PLANT", "crop": "MELON"}
        self.assertEqual(L.outstanding_melon_units(obs), 24)
        self.assertEqual(L.max_new_melon_plants(obs, 36), 2)

    def test_small_certificate_blocks_only_melon(self):
        props = [
            {"crop": "MELON", "tiles": [0, 1, 2], "seed_units": 3},
            {"crop": "CARROT", "tiles": [3, 4, 5]},
        ]
        out = L.filter_proposals_with_realization_bound(props, base_observation(), 6)
        self.assertEqual(out, [props[0] | {"tiles": [0], "seed_units": 1}, props[1]])

    def test_batch_budget_is_aggregate(self):
        props = [
            {"crop": "MELON", "tiles": [0, 1, 2], "seed_units": 3},
            {"crop": "MELON", "tiles": [3, 4, 5], "seed_units": 3},
        ]
        out = L.filter_proposals_with_realization_bound(props, base_observation(), 24)
        self.assertEqual([len(p["tiles"]) for p in out], [3, 1])
        self.assertEqual([p["seed_units"] for p in out], [3, 1])

    def test_malformed_melon_proposal_fails_whole_batch_to_identity(self):
        props = [
            {"crop": "MELON", "tiles": [0, 1], "size": 3},
            {"crop": "MELON", "tiles": [2, 3]},
        ]
        self.assertIs(L.filter_proposals_with_realization_bound(props, base_observation(), 60), props)

    def test_indivisible_seed_units_fail_to_identity(self):
        props = [{"crop": "MELON", "tiles": [0, 1, 2], "seed_units": 2}]
        self.assertIs(L.filter_proposals_with_realization_bound(props, base_observation(), 6), props)

    def test_malformed_custody_fails_to_identity(self):
        props = [{"crop": "MELON", "tiles": [0, 1]}]
        obs = base_observation()
        obs["private"]["shed"]["MELON"] = True
        self.assertIs(L.filter_proposals_with_realization_bound(props, obs, 60), props)

    def test_inputs_are_not_mutated(self):
        obs = base_observation()
        props = [{"crop": "MELON", "tiles": list(range(6)), "seed_units": 6}]
        before_obs = copy.deepcopy(obs)
        before_props = copy.deepcopy(props)
        L.filter_proposals_with_realization_bound(props, obs, 12)
        self.assertEqual(obs, before_obs)
        self.assertEqual(props, before_props)


if __name__ == "__main__":
    unittest.main()
