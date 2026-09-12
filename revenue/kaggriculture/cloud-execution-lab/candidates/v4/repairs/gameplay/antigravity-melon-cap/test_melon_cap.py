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


def _tiles(plants):
    return [(5 + (i % 5), 5 + (i // 5)) for i in range(plants)]


def melon_proposal(plants, *, routes=("A", "B"), outer=None):
    """Minimal faithful FourthQuadrant MELON proposal shape."""
    tiles = _tiles(plants)
    variants = {}
    for route_index, route in enumerate(routes):
        land_step = 80 + route_index * 200
        patches = {
            land_step: {
                "market": [
                    ["BUY_LAND"],
                    ["BUY_SEED", "MELON", plants],
                    ["HIRE"],
                ]
            }
        }
        lots = []
        for i, tile in enumerate(tiles):
            plant_step = land_step + 10 + i
            patches[plant_step] = {"hands": [["PLANT", "MELON"]]}
            lots.append({
                "tile": list(tile),
                "crop": "MELON",
                "plant_step": plant_step,
                "water_steps": [],
                "harvest_step": plant_step + 10,
                "worker": 1,
                "drop_step": plant_step + 11,
                "sale_step": plant_step + 11,
                "sale_slot": 0,
            })
        variants[route] = {
            "patches": patches,
            "bundle": {
                "route_id": route,
                "base_route_id": route,
                "target_quadrant": "SE",
                "land": {"step": land_step, "slot": 0},
                "lots": lots,
            },
        }
    proposal = {
        "crop": "MELON",
        "tiles": tiles,
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

    def test_executable_cardinality_is_bound_to_lots_patches_and_seed_order(self):
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

    def test_buy_seed_quantity_mismatch_fails_closed(self):
        proposal = melon_proposal(3)
        proposal["variants"]["A"]["patches"][80]["market"][1] = ["BUY_SEED", "MELON", 5]
        self.assertIsNone(M.executable_melon_plants(proposal))
        self.assertEqual(M.filter_proposals([proposal], base_observation()), [])

    def test_bool_buy_seed_quantity_fails_closed(self):
        proposal = melon_proposal(1)
        proposal["variants"]["A"]["patches"][80]["market"][1] = ["BUY_SEED", "MELON", True]
        self.assertIsNone(M.executable_melon_plants(proposal))

    def test_land_slot_must_bind_producer_owned_seed_order(self):
        proposal = melon_proposal(2)
        proposal["variants"]["A"]["bundle"]["land"]["slot"] = 1
        self.assertIsNone(M.executable_melon_plants(proposal))

    def test_route_variant_disagreement_fails_closed(self):
        proposal = melon_proposal(4)
        proposal["variants"]["B"]["bundle"]["lots"].pop()
        self.assertIsNone(M.executable_melon_plants(proposal))
        self.assertEqual(M.filter_proposals([proposal], base_observation()), [])

    def test_outer_metadata_cannot_understate_executable_contract(self):
        proposal = melon_proposal(5)
        proposal["tiles"] = proposal["tiles"][:4]
        proposal["seed_units"] = 4
        proposal["size"] = 4
        self.assertIsNone(M.executable_melon_plants(proposal))
        self.assertEqual(M.filter_proposals([proposal], base_observation()), [])

    def test_lot_tile_mismatch_fails_closed(self):
        proposal = melon_proposal(3)
        proposal["variants"]["A"]["bundle"]["lots"][1]["tile"] = [9, 9]
        self.assertIsNone(M.executable_melon_plants(proposal))

    def test_lot_worker_patch_action_must_authenticate(self):
        proposal = melon_proposal(3)
        lot = proposal["variants"]["A"]["bundle"]["lots"][1]
        proposal["variants"]["A"]["patches"][lot["plant_step"]]["hands"][0] = ["PASS"]
        self.assertIsNone(M.executable_melon_plants(proposal))
        self.assertEqual(M.filter_proposals([proposal], base_observation()), [])

    def test_duplicate_outer_tile_fails_closed(self):
        proposal = melon_proposal(3)
        proposal["tiles"][1] = proposal["tiles"][0]
        self.assertIsNone(M.executable_melon_plants(proposal))

    def test_duplicate_plant_slot_fails_closed(self):
        proposal = melon_proposal(3)
        lots = proposal["variants"]["A"]["bundle"]["lots"]
        lots[1]["plant_step"] = lots[0]["plant_step"]
        lots[1]["worker"] = lots[0]["worker"]
        self.assertIsNone(M.executable_melon_plants(proposal))

    def test_malformed_patch_payload_fails_closed(self):
        proposal = melon_proposal(1)
        lot = proposal["variants"]["A"]["bundle"]["lots"][0]
        proposal["variants"]["A"]["patches"][lot["plant_step"]]["hands"] = [None]
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
