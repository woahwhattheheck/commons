# SPDX-License-Identifier: Apache-2.0
import copy
import json
import unittest

from land_unlock_jit import (
    LandUnlockError,
    apply_relocation,
    audit_routes,
    census_route,
    propose_relocations,
    quadrant_of,
)


def row(farmer=("PASS",), hands=(), market=()):
    return {
        "farmer": list(farmer),
        "hands": [list(action) for action in hands],
        "market": [list(order) for order in market],
    }


def blank_route(length=24):
    return [row() for _ in range(length)]


class LandUnlockJITTests(unittest.TestCase):
    def test_locked_tile_movement_is_not_the_deadline(self):
        route = blank_route()
        route[0] = row(market=(("BUY_LAND",),))
        route[1] = row(farmer=("EAST",))
        route[2] = row(farmer=("EAST",))
        route[3] = row(farmer=("WEST",))
        route[4] = row(farmer=("EAST",), market=(("HIRE",), ()))
        route[5] = row(farmer=("PLANT", "WHEAT"), hands=(("PASS",),))

        use = census_route(route, "r", checkpoints=())[0]
        self.assertEqual(use.target_quadrant, "NE")
        self.assertEqual(use.first_move_step, 1)
        self.assertEqual(use.first_effect_step, 5)
        self.assertEqual(use.first_effect_action, ("PLANT", "WHEAT"))
        self.assertEqual(use.first_effect_position, (6, 4))

        plan = propose_relocations(route, "r", checkpoints=())[0]
        self.assertEqual((plan.purchase_step, plan.target_step), (0, 4))
        self.assertEqual((plan.purchase_slot, plan.target_slot), (0, 1))
        self.assertEqual(plan.saved_cash_turns, 4)

    def test_market_on_effect_step_is_too_late(self):
        route = blank_route(8)
        route[0] = row(market=(("BUY_LAND",),))
        route[1] = row(farmer=("EAST",))
        route[2] = row(farmer=("EAST",), market=((),))
        route[3] = row(farmer=("PLANT", "WHEAT"), market=((),))
        plans = propose_relocations(route, "r", checkpoints=())
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].target_step, 2)

    def test_literal_empty_must_be_trailing(self):
        route = blank_route(8)
        route[0] = row(market=(("BUY_LAND",),))
        route[1] = row(farmer=("EAST",))
        route[2] = row(farmer=("PASS",), market=((), ("HIRE",)))
        route[3] = row(farmer=("PLANT", "WHEAT"))
        self.assertEqual(propose_relocations(route, "r", checkpoints=()), ())

    def test_checkpoint_boundary_rejects_later_slot(self):
        route = blank_route(12)
        route[0] = row(market=(("BUY_LAND",),))
        route[1] = row(farmer=("EAST",))
        route[7] = row(market=((),))
        route[8] = row(farmer=("PLANT", "WHEAT"))
        self.assertEqual(propose_relocations(route, "r", checkpoints=(6,)), ())

    def test_relocation_never_crosses_original_day(self):
        route = blank_route(30)
        route[0] = row(market=(("BUY_LAND",),))
        route[1] = row(farmer=("EAST",))
        route[23] = row(market=((),))
        route[24] = row(farmer=("EAST",))
        route[26] = row(farmer=("PLANT", "WHEAT"))
        plan = propose_relocations(route, "r", checkpoints=())[0]
        self.assertEqual(plan.target_step, 23)

    def test_apply_moves_only_two_slots_and_preserves_multiplicity(self):
        route = blank_route()
        route[0] = row(market=(("BUY_LAND",), ("BUY_SEED", "WHEAT", 3)))
        route[1] = row(farmer=("EAST",))
        route[4] = row(market=(("HIRE",), ()))
        route[5] = row(farmer=("PLANT", "WHEAT"), hands=(("PASS",),))
        before = copy.deepcopy(route)
        plan = propose_relocations(route, "r", checkpoints=())[0]
        changed = apply_relocation(route, plan)

        self.assertEqual(route, before)
        self.assertEqual(changed[0]["market"][0], [])
        self.assertEqual(changed[4]["market"][1], ["BUY_LAND"])
        self.assertEqual(changed[0]["market"][1], ["BUY_SEED", "WHEAT", 3])
        for step in range(len(route)):
            if step not in (0, 4):
                self.assertEqual(changed[step], route[step])
        self.assertEqual(
            sum(order == ["BUY_LAND"] for r in changed for order in r["market"]),
            1,
        )

    def test_apply_rejects_drifted_source_or_target(self):
        route = blank_route()
        route[0] = row(market=(("BUY_LAND",),))
        route[1] = row(farmer=("EAST",))
        route[4] = row(market=((),))
        route[5] = row(farmer=("PLANT", "WHEAT"))
        plan = propose_relocations(route, "r", checkpoints=())[0]

        drifted = copy.deepcopy(route)
        drifted[0]["market"][0] = ["HIRE"]
        with self.assertRaises(LandUnlockError):
            apply_relocation(drifted, plan)

        drifted = copy.deepcopy(route)
        drifted[4]["market"][0] = ["SELL", "WHEAT", 1]
        with self.assertRaises(LandUnlockError):
            apply_relocation(drifted, plan)

    def test_animal_place_is_land_dependent_but_shed_place_is_not(self):
        animal = blank_route(10)
        animal[0] = row(market=(("BUY_LAND",),))
        animal[1] = row(farmer=("EAST",))
        animal[2] = row(farmer=("PLACE", "COW"))
        use = census_route(animal, "animal", checkpoints=())[0]
        self.assertEqual((use.first_effect_step, use.first_effect_action), (2, ("PLACE", "COW")))

        product = blank_route(10)
        product[0] = row(market=(("BUY_LAND",),))
        product[1] = row(farmer=("EAST",))
        product[2] = row(farmer=("PLACE", "WHEAT", 1))
        use = census_route(product, "product", checkpoints=())[0]
        self.assertIsNone(use.first_effect_step)

    def test_hired_hand_spawn_and_effect_are_censused(self):
        route = blank_route(12)
        route[0] = row(market=(("BUY_LAND",), ("HIRE",)))
        route[1] = row(farmer=("PASS",), hands=(("EAST",),))
        route[2] = row(farmer=("PASS",), hands=(("PLANT", "CARROT"),))
        use = census_route(route, "r", checkpoints=())[0]
        self.assertEqual(use.first_effect_worker, 1)
        self.assertEqual(use.first_effect_position, (6, 4))

    def test_multiple_purchases_map_land_order(self):
        route = blank_route(30)
        route[0] = row(market=(("BUY_LAND",),))
        route[1] = row(market=(("BUY_LAND",),))
        route[2] = row(market=(("BUY_LAND",),))
        uses = census_route(route, "r", checkpoints=())
        self.assertEqual([use.target_quadrant for use in uses], ["NE", "SW", "SE"])

    def test_off_prefix_buy_land_is_not_counted(self):
        market = [()] * 10 + [("BUY_LAND",)]
        route = blank_route(4)
        route[0] = row(market=market)
        self.assertEqual(census_route(route, "r", max_orders=10, checkpoints=()), ())

    def test_audit_is_deterministic_and_json_serializable(self):
        a = blank_route(8)
        a[0] = row(market=(("BUY_LAND",),))
        a[1] = row(farmer=("EAST",))
        a[2] = row(market=((),))
        a[3] = row(farmer=("PLANT", "WHEAT"))
        report1 = audit_routes({"z": a, "a": blank_route(8)}, checkpoints=())
        report2 = audit_routes({"a": blank_route(8), "z": a}, checkpoints=())
        self.assertEqual(report1, report2)
        self.assertEqual(report1["route_count"], 2)
        self.assertEqual(report1["purchase_count"], 1)
        self.assertEqual(report1["relocation_count"], 1)
        json.dumps(report1, sort_keys=True)

    def test_malformed_inputs_fail_closed(self):
        with self.assertRaises(LandUnlockError):
            quadrant_of((0, 0), board_size=9)
        with self.assertRaises(LandUnlockError):
            census_route([{"market": "bad"}], "r")
        with self.assertRaises(LandUnlockError):
            audit_routes({})


if __name__ == "__main__":
    unittest.main()
