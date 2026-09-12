import copy
import unittest

from animal_headroom_harvest import plan_animal_headroom_harvest


CFG = {"turnsPerDay": 24, "shedCapacity": 100}


def animal():
    return {
        "kind": "COOP",
        "animal": "GOOSE",
        "placed_day": 0,
        "yield_units": 4,
        "consecutive_unfed": 0,
        "fed_today": True,
        "cared_today": False,
        "fertilizer_available": False,
        "pending_care_bonus": 0,
    }


def state_with_hand(*, shed_wheat=0, inventories=None):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    tiles[1][1] = animal()
    farm = {"farmer": [1, 1], "hands": [[2, 1]], "tiles": tiles}
    return {
        "player": 0,
        "farms": [farm],
        "private": {
            "shed": {"WHEAT": shed_wheat},
            "inventories": copy.deepcopy(inventories if inventories is not None else [{}, {}]),
        },
        "day": 4,
        "hour": 23,
    }


def action_with_hand():
    return {"farmer": ["PASS"], "hands": [["PASS"]], "market": []}


class ActorInventoryTrustBoundaryTests(unittest.TestCase):
    def test_exact_actor_inventory_cardinality_remains_eligible(self):
        obs = state_with_hand(shed_wheat=90, inventories=[{}, {"WHEAT": 3}])
        plan = plan_animal_headroom_harvest(action_with_hand(), obs, CFG)
        self.assertTrue(plan["eligible"])
        self.assertEqual(plan["capacity"]["current_private_goods"], 93)

    def test_truncated_inventory_vector_is_malformed_not_capacity_safe(self):
        complete = state_with_hand(shed_wheat=96, inventories=[{}, {"WHEAT": 1}])
        complete_plan = plan_animal_headroom_harvest(action_with_hand(), complete, CFG)
        self.assertFalse(complete_plan["eligible"])
        self.assertEqual(complete_plan["reason"], "eod_shed_capacity_not_certified")

        truncated = copy.deepcopy(complete)
        truncated["private"]["inventories"] = [{}]
        truncated_plan = plan_animal_headroom_harvest(action_with_hand(), truncated, CFG)
        self.assertFalse(truncated_plan["eligible"])
        self.assertEqual(truncated_plan["reason"], "malformed_capacity_state")

    def test_extra_inventory_vector_is_malformed(self):
        obs = state_with_hand(inventories=[{}, {}, {}])
        plan = plan_animal_headroom_harvest(action_with_hand(), obs, CFG)
        self.assertFalse(plan["eligible"])
        self.assertEqual(plan["reason"], "malformed_capacity_state")

    def test_farmer_only_requires_single_inventory_row(self):
        obs = state_with_hand(inventories=[{}, {}])
        obs["farms"][0]["hands"] = []
        obs["private"]["inventories"] = [{}]
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        plan = plan_animal_headroom_harvest(action, obs, CFG)
        self.assertTrue(plan["eligible"])

    def test_farmer_only_rejects_stale_hand_inventory_row(self):
        obs = state_with_hand(inventories=[{}, {}])
        obs["farms"][0]["hands"] = []
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        plan = plan_animal_headroom_harvest(action, obs, CFG)
        self.assertFalse(plan["eligible"])
        self.assertEqual(plan["reason"], "malformed_capacity_state")


if __name__ == "__main__":
    unittest.main()
