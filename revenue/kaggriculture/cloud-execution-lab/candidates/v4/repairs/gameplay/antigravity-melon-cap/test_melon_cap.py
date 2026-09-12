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


def producer_proposal(tiles, route_ids=("r0", "r1"), start_step=300):
    """Minimal faithful FourthQuadrant MELON proposal shape."""
    tiles = [tuple(tile) for tile in tiles]
    variants = {}
    for route_index, route_id in enumerate(route_ids):
        patches = {}
        lots = []
        for index, tile in enumerate(tiles):
            step = start_step + route_index * 100 + index
            worker = 1 + (index % 2)
            hands = [["PASS"] for _ in range(worker)]
            hands[worker - 1] = ["PLANT", "MELON"]
            patches[step] = {"farmer": ["PASS"], "hands": hands, "market": []}
            lots.append({
                "tile": list(tile),
                "crop": "MELON",
                "plant_step": step,
                "water_steps": [],
                "harvest_step": step + 10,
                "worker": worker,
                "drop_step": step + 11,
                "sale_step": step + 11,
                "sale_slot": 0,
            })
        variants[route_id] = {
            "patches": patches,
            "receipts": [],
            "costs": [],
            "worker_days": [],
            "bundle": {
                "route_id": route_id,
                "base_route_id": route_id,
                "target_quadrant": "SE",
                "land": {"step": start_step, "slot": 0},
                "rejoin_step": 600,
                "lots": lots,
            },
        }
    return {
        "crop": "MELON",
        "tiles": tiles,
        "workers": 2,
        "start": start_step,
        "variants": variants,
        "seed_units": len(tiles),
        "cost": 4000,
    }


def executable_patch_plants(proposal):
    counts = []
    for variant in proposal["variants"].values():
        count = 0
        for row in variant["patches"].values():
            for action in row.get("hands", []):
                if action == ["PLANT", "MELON"]:
                    count += 1
        counts.append(count)
    return counts


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

    def test_batch_budget_admits_whole_proposals_only(self):
        obs = base_observation()
        first = producer_proposal([(5, 5), (6, 5), (5, 6)])
        second = producer_proposal([(7, 5), (6, 6), (5, 7)], start_step=400)
        carrot = {"crop": "CARROT", "tiles": list(range(9))}
        out = M.filter_proposals([first, second, carrot], obs)
        self.assertEqual(out, [first, carrot])
        self.assertEqual(M.executable_melon_plants(first), 3)
        self.assertEqual(executable_patch_plants(first), [3, 3])

    def test_metadata_shrink_cannot_smuggle_original_executable_body(self):
        obs = base_observation()
        proposal = producer_proposal([(5, 5), (6, 5), (5, 6), (6, 6), (7, 5), (5, 7)])
        self.assertEqual(executable_patch_plants(proposal), [6, 6])
        self.assertEqual(M.max_melon_plants(obs), 4)
        self.assertEqual(M.filter_proposals([proposal], obs), [])

    def test_outer_metadata_and_executable_lots_must_agree(self):
        proposal = producer_proposal([(5, 5), (6, 5), (5, 6)])
        proposal["tiles"] = proposal["tiles"][:1]
        proposal["seed_units"] = 1
        self.assertIsNone(M.executable_melon_plants(proposal))
        self.assertEqual(M.filter_proposals([proposal], base_observation()), [])

    def test_patch_action_must_authenticate_each_lot(self):
        proposal = producer_proposal([(5, 5), (6, 5), (5, 6)])
        variant = proposal["variants"]["r0"]
        lot = variant["bundle"]["lots"][1]
        variant["patches"][lot["plant_step"]]["hands"][lot["worker"] - 1] = ["PASS"]
        self.assertIsNone(M.executable_melon_plants(proposal))
        self.assertEqual(M.filter_proposals([proposal], base_observation()), [])

    def test_every_route_variant_must_agree(self):
        proposal = producer_proposal([(5, 5), (6, 5), (5, 6)])
        proposal["variants"]["r1"]["bundle"]["lots"].pop()
        self.assertIsNone(M.executable_melon_plants(proposal))

    def test_metadata_only_melon_fails_closed_but_other_crop_passes(self):
        melon = {"crop": "MELON", "tiles": [(5, 5), (6, 5)], "seed_units": 2}
        carrot = {"crop": "CARROT", "tiles": [3, 4]}
        self.assertEqual(M.filter_proposals([melon, carrot], base_observation()), [carrot])

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
            producer_proposal([(5, 5), (6, 5)]),
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
        props = [producer_proposal([(5, 5), (6, 5), (5, 6), (6, 6), (7, 5), (5, 7)])]
        before = copy.deepcopy(props)
        M.filter_proposals(props, obs)
        self.assertEqual(props, before)


if __name__ == "__main__":
    unittest.main()
