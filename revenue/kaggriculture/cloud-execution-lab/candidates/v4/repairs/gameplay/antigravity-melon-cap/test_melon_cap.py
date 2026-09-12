import copy
import sys
import unittest
from pathlib import Path

import melon_cap as M

HERE = Path(__file__).resolve()
LAB = next((parent for parent in HERE.parents if (parent / "fourth_quadrant.py").is_file()), None)
if LAB is not None and str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))
try:
    import fourth_quadrant as FQ
except ModuleNotFoundError:
    FQ = None


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

    def test_mutually_exclusive_alternatives_do_not_spend_each_other_budget(self):
        obs = base_observation()
        three = nested_proposal(3)
        four = nested_proposal(4)
        five = nested_proposal(5)
        carrot = {"crop": "CARROT", "tiles": list(range(9))}
        out = M.filter_proposals([three, four, five, carrot], obs)
        self.assertEqual(out, [three, four, carrot])
        self.assertIs(out[0], three)
        self.assertIs(out[1], four)

    def test_variant_cardinality_mismatch_fails_closed(self):
        obs = base_observation()
        proposal = nested_proposal(4, route_ids=("r", "alt"))
        proposal["variants"]["alt"]["patches"].pop(603)
        self.assertIsNone(M.executable_melon_plants(proposal))
        self.assertEqual(M.filter_proposals([proposal], obs), [])

    def test_shallow_metadata_cannot_hide_oversized_executable_variant(self):
        obs = base_observation()
        proposal = nested_proposal(5)
        proposal["tiles"] = [0, 1, 2, 3]
        proposal["seed_units"] = 4
        self.assertIsNone(M.executable_melon_plants(proposal))
        self.assertEqual(M.filter_proposals([proposal], obs), [])

    def test_sold_plus_held_plus_planted_can_close_budget(self):
        obs = base_observation()
        obs["farms"][0]["sale_counters"]["MELON"] = 10
        obs["private"]["shed"]["MELON"] = 7
        obs["farms"][0]["tiles"][0][0] = {"kind": "PLANT", "crop": "MELON"}
        obs["farms"][0]["tiles"][0][1] = {"kind": "PLANT", "crop": "MELON"}
        self.assertEqual(M.committed_melon_units(obs), 29)
        self.assertEqual(M.max_melon_plants(obs), 0)

    def test_malformed_custody_fails_closed_for_melon_only(self):
        props = [nested_proposal(2), {"crop": "CARROT", "tiles": [3, 4]}]
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
        props = [nested_proposal(5)]
        before = copy.deepcopy(props)
        M.filter_proposals(props, obs)
        self.assertEqual(props, before)

    @unittest.skipIf(FQ is None, "repository fourth_quadrant module not mounted")
    def test_fourth_quadrant_producer_filter_consumer_contract(self):
        class Mechanics:
            CROPS = {"CARROT": {"seed": 1}, "TOMATO": {"seed": 1}, "MELON": {"seed": 1}}

            @staticmethod
            def _hire_cost(_hands, _mult):
                return 1

        obs = {
            "player": 0,
            "step": 11 * 24,
            "farms": [{
                "sale_counters": {"MELON": 0},
                "tiles": [["LOCKED" for _ in range(10)] for _ in range(10)],
                "unlocked_quadrants": ["NW", "NE", "SW"],
                "hands": [],
                "farmer": [4, 4],
            }],
            "private": {"shed": {"MELON": 0}, "inventories": []},
            "market": {"inventory": {"MELON": 10000}},
        }
        route = [{"farmer": ["PASS"], "hands": [], "market": []} for _ in range(720)]
        options = FQ.proposals(Mechanics(), obs, {"r": route}, "r",
                               {"maxMarketOrdersPerTurn": 10, "farmHandCostMult": 1})
        melons = [p for p in options if p.get("crop") == "MELON"]
        self.assertTrue(any(len(p["tiles"]) == 4 for p in melons))
        self.assertTrue(any(len(p["tiles"]) == 5 for p in melons))

        filtered = M.filter_proposals(melons, obs)
        sizes = {len(p["tiles"]) for p in filtered}
        self.assertIn(4, sizes)
        self.assertNotIn(5, sizes)
        for proposal in filtered:
            candidate, _bundle = FQ.economic_program(proposal, "r", route)
            executed = sum(
                1 for row in candidate for action in row.get("hands", [])
                if isinstance(action, (list, tuple)) and action[:2] == ["PLANT", "MELON"]
            )
            self.assertEqual(executed, len(proposal["tiles"]))
            self.assertLessEqual(executed, 4)


if __name__ == "__main__":
    unittest.main()
