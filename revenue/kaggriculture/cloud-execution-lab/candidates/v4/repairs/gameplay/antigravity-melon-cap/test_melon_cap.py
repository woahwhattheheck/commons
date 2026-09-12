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

    def test_batch_budget_is_consumed_across_proposals(self):
        obs = base_observation()
        props = [
            {"crop": "MELON", "tiles": [0, 1, 2], "seed_units": 3},
            {"crop": "MELON", "tiles": [3, 4, 5], "seed_units": 3},
            {"crop": "CARROT", "tiles": list(range(9))},
        ]
        out = M.filter_proposals(props, obs)
        melon_sizes = [len(p["tiles"]) for p in out if isinstance(p, dict) and p.get("crop") == "MELON"]
        self.assertEqual(melon_sizes, [3, 1])
        self.assertEqual(sum(melon_sizes), 4)
        self.assertEqual(out[-1], props[-1])

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
            {"crop": "MELON", "tiles": [1, 2]},
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
        props = [{"crop": "MELON", "tiles": list(range(6)), "seed_units": 6}]
        before = copy.deepcopy(props)
        M.filter_proposals(props, obs)
        self.assertEqual(props, before)


if __name__ == "__main__":
    unittest.main()
