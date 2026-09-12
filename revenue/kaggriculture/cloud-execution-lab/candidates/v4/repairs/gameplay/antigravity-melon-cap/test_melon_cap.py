import copy
import unittest

import melon_cap as M


def base_observation():
    return {
        "player": 0,
        "step": 600,
        "farms": [{
            "sale_counters": {"MELON": 0},
            "tiles": [[None for _ in range(3)] for _ in range(3)],
        }],
        "private": {
            "shed": {"MELON": 0, "WHEAT": 0},
            "inventories": [{}, {}],
        },
        "market": {"inventory": {"MELON": 9975}},
    }


def melon_proposal(plants, *, routes=("A", "B"), outer=None):
    variants = {}
    for route in routes:
        patches = {
            100 + i: {"hands": [["PLANT", "MELON"]]}
            for i in range(plants)
        }
        variants[route] = {"patches": patches}
    proposal = {
        "crop": "MELON",
        "tiles": list(range(plants)),
        "seed_units": plants,
        "variants": variants,
    }
    if outer:
        proposal.update(outer)
    return proposal


class MelonCapTests(unittest.TestCase):
    def test_empty_commitment_allows_four_tiles(self):
        self.assertEqual(M.remaining_melon_budget(base_observation()), 28)
        self.assertEqual(M.max_melon_plants(base_observation()), 4)

    def test_existing_plants_reserve_max_future_yield(self):
        obs = base_observation()
        obs["farms"][0]["tiles"][0][0] = {"kind": "PLANT", "crop": "MELON", "yield_units": 1}
        obs["farms"][0]["tiles"][0][1] = {"kind": "PLANT", "crop": "MELON", "yield_units": 6}
        self.assertEqual(M.planted_melon_reserve(obs), 12)
        self.assertEqual(M.max_melon_plants(obs), 2)

    def test_held_melon_reserves_budget(self):
        obs = base_observation()
        obs["private"]["shed"]["MELON"] = 10
        obs["private"]["inventories"][1]["MELON"] = 6
        self.assertEqual(M.held_melon_units(obs), 16)
        self.assertEqual(M.max_melon_plants(obs), 2)

    def test_executable_cardinality_is_derived_from_all_variants(self):
        proposal = melon_proposal(4)
        self.assertEqual(M.executable_melon_plants(proposal), 4)

    def test_whole_proposal_admission_preserves_identity(self):
        obs = base_observation()
        proposal = melon_proposal(4)
        out = M.filter_proposals([proposal], obs)
        self.assertEqual(out, [proposal])
        self.assertIs(out[0], proposal)

    def test_oversize_is_dropped_not_shrunk_and_later_smaller_can_fit(self):
        obs = base_observation()
        too_big = melon_proposal(5)
        three = melon_proposal(3)
        one = melon_proposal(1)
        out = M.filter_proposals([too_big, three, one], obs)
        self.assertEqual(out, [three, one])
        self.assertIs(out[0], three)
        self.assertIs(out[1], one)

    def test_mutually_exclusive_alternatives_do_not_consume_each_other(self):
        obs = base_observation()
        three = melon_proposal(3)
        four = melon_proposal(4)
        carrot = {"crop": "CARROT", "tiles": list(range(9))}
        out = M.filter_proposals([three, four, carrot], obs)
        self.assertEqual(out, [three, four, carrot])
        self.assertIs(out[0], three)
        self.assertIs(out[1], four)

    def test_route_variant_disagreement_fails_closed(self):
        proposal = melon_proposal(4)
        proposal["variants"]["B"]["patches"][999] = {"hands": [["PLANT", "MELON"]]}
        self.assertIsNone(M.executable_melon_plants(proposal))
        self.assertEqual(M.filter_proposals([proposal], base_observation()), [])

    def test_outer_metadata_cannot_understate_executable_patches(self):
        proposal = melon_proposal(5)
        proposal["tiles"] = proposal["tiles"][:4]
        proposal["seed_units"] = 4
        proposal["size"] = 4
        self.assertIsNone(M.executable_melon_plants(proposal))
        self.assertEqual(M.filter_proposals([proposal], base_observation()), [])

    def test_malformed_patch_payload_fails_closed(self):
        proposal = melon_proposal(1)
        proposal["variants"]["A"]["patches"][100]["hands"] = [None]
        self.assertIsNone(M.executable_melon_plants(proposal))
        self.assertEqual(M.filter_proposals([proposal], base_observation()), [])

    def test_sold_plus_held_plus_planted_can_close_budget(self):
        obs = base_observation()
        obs["farms"][0]["sale_counters"]["MELON"] = 10
        obs["private"]["shed"]["MELON"] = 7
        obs["farms"][0]["tiles"][0][0] = {"kind": "PLANT", "crop": "MELON"}
        obs["farms"][0]["tiles"][0][1] = {"kind": "PLANT", "crop": "MELON"}
        self.assertEqual(M.committed_melon_units(obs), 29)
        self.assertEqual(M.max_melon_plants(obs), 0)

    def test_malformed_custody_fails_closed_for_melon_only(self):
        props = [
            melon_proposal(2),
            {"crop": "CARROT", "tiles": [3, 4]},
        ]
        out = M.filter_proposals(props, {"player": "0"})
        self.assertEqual(out, [props[1]])
        self.assertEqual(M.remaining_melon_budget(None), 0)

    def test_market_drift_fallback_uses_exact_prior_town_ticks(self):
        obs = base_observation()
        del obs["farms"][0]["sale_counters"]
        obs["step"] = 25
        obs["market"]["inventory"]["MELON"] = 10008
        self.assertEqual(M.lifetime_melon_sold(obs), 10)

    def test_bool_numeric_aliases_fail_closed(self):
        obs = base_observation()
        obs["private"]["shed"]["MELON"] = True
        self.assertEqual(M.remaining_melon_budget(obs), 0)

    def test_input_is_not_mutated(self):
        obs = base_observation()
        props = [melon_proposal(5)]
        before = copy.deepcopy(props)
        M.filter_proposals(props, obs)
        self.assertEqual(props, before)


if __name__ == "__main__":
    unittest.main()
