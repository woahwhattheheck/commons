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


def nested_proposal(plants, route_ids=("r",), crop="MELON"):
    variants = {}
    for route_id in route_ids:
        patches = {}
        for i in range(plants):
            step = 600 + i
            patches[step] = {"farmer": ["PASS"], "hands": [["PLANT", crop]]}
        variants[route_id] = {
            "patches": patches,
            "worker_days": [{"day": 25, "kind": "plant", "incumbent_hands": 0}],
            "bundle": {"lots": []},
        }
    return {
        "crop": crop,
        "tiles": list(range(plants)),
        "workers": 1,
        "seed_units": plants,
        "variants": variants,
    }


class RealizationBoundTests(unittest.TestCase):
    def test_missing_certificate_is_exact_identity(self):
        props = [nested_proposal(8)]
        self.assertIs(L.filter_proposals_with_realization_bound(props, base_observation(), None), props)

    def test_bad_certificate_is_exact_identity(self):
        props = [nested_proposal(2)]
        self.assertIs(L.filter_proposals_with_realization_bound(props, base_observation(), True), props)
        self.assertIs(L.filter_proposals_with_realization_bound(props, base_observation(), -1), props)

    def test_large_certificate_can_exceed_legacy_four_plant_cap(self):
        props = [nested_proposal(10)]
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

    def test_small_certificate_drops_whole_oversized_melon_only(self):
        melon = nested_proposal(3)
        carrot = {"crop": "CARROT", "tiles": [3, 4, 5]}
        out = L.filter_proposals_with_realization_bound(
            [melon, carrot], base_observation(), 6
        )
        self.assertEqual(out, [carrot])
        self.assertIs(out[0], carrot)

    def test_mutually_exclusive_alternatives_do_not_spend_each_other_budget(self):
        three = nested_proposal(3)
        four = nested_proposal(4)
        five = nested_proposal(5)
        carrot = {"crop": "CARROT", "tiles": [9]}
        out = L.filter_proposals_with_realization_bound(
            [three, four, five, carrot], base_observation(), 24
        )
        self.assertEqual(out, [three, four, carrot])
        self.assertIs(out[0], three)
        self.assertIs(out[1], four)

    def test_valid_alternatives_preserve_batch_identity_when_nothing_filtered(self):
        props = [nested_proposal(3), nested_proposal(4)]
        self.assertIs(
            L.filter_proposals_with_realization_bound(props, base_observation(), 24),
            props,
        )

    def test_variant_cardinality_mismatch_is_dropped_not_whole_batch_identity(self):
        bad = nested_proposal(4, route_ids=("r", "alt"))
        bad["variants"]["alt"]["patches"].pop(603)
        good = nested_proposal(2)
        out = L.filter_proposals_with_realization_bound(
            [bad, good], base_observation(), 60
        )
        self.assertEqual(out, [good])
        self.assertIs(out[0], good)

    def test_shallow_metadata_cannot_hide_oversized_executable_variant(self):
        bad = nested_proposal(5)
        bad["tiles"] = [0, 1, 2, 3]
        bad["seed_units"] = 4
        out = L.filter_proposals_with_realization_bound(
            [bad], base_observation(), 24
        )
        self.assertEqual(out, [])

    def test_malformed_custody_fails_to_exact_identity(self):
        props = [nested_proposal(2)]
        obs = base_observation()
        obs["private"]["shed"]["MELON"] = True
        self.assertIs(L.filter_proposals_with_realization_bound(props, obs, 60), props)

    def test_inputs_are_not_mutated(self):
        obs = base_observation()
        props = [nested_proposal(6)]
        before_obs = copy.deepcopy(obs)
        before_props = copy.deepcopy(props)
        L.filter_proposals_with_realization_bound(props, obs, 12)
        self.assertEqual(obs, before_obs)
        self.assertEqual(props, before_props)


if __name__ == "__main__":
    unittest.main()
