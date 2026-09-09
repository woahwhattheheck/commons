# SPDX-License-Identifier: Apache-2.0
"""P21 contracts against the repository's extracted Kaggriculture mechanics."""
from copy import deepcopy
import unittest

import mechanics as m
from terminal_route_value import certify_candidate


def row(hands=0, market=None):
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in range(hands)],
            "market": [] if market is None else deepcopy(market)}


def observation(step, *, farmer=(4, 4), hands=(), shed=None, inventories=None):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    farm = {"farmer": list(farmer), "hands": [list(p) for p in hands], "money": 1000,
            "hires_today": len(hands), "unlocked_quadrants": ["NW"], "tiles": tiles}
    rival = {"farmer": [4, 4], "hands": [], "money": 1000,
             "hires_today": 0, "unlocked_quadrants": ["NW"],
             "tiles": [[None for _ in range(10)] for _ in range(10)]}
    private = {"shed": {} if shed is None else deepcopy(shed),
               "inventories": ([{} for _ in range(1 + len(hands))]
                               if inventories is None else deepcopy(inventories)),
               "seeds": {}}
    return {"step": step, "player": 0, "farms": [farm, rival], "private": private,
            "market": {"inventory": {p: 10000 for p in m.PRODUCTS}}}


class TerminalRouteValueEngineTests(unittest.TestCase):
    def test_actual_market_price_for_carried_milk_at_718(self):
        obs = observation(718, inventories=[{"MILK": 1}])
        route = [row() for _ in range(720)]
        candidate, report = certify_candidate(m, obs, {}, route, worker=0,
                                              carried_product="MILK")
        self.assertTrue(report["certified"])
        self.assertEqual(candidate.unit_actions, (("DROP",),))
        self.assertEqual(candidate.quiet_incremental_cash,
                         m.market_price("MILK", 10000))

    def test_actual_wheat_maturity_boundary(self):
        obs = observation(712, farmer=(3, 4))
        immature = m._new_plant("WHEAT", 28, 24)
        immature["yield_units"] = 1
        obs["farms"][0]["tiles"][4][3] = immature
        route = [row() for _ in range(720)]
        candidate, report = certify_candidate(m, obs, {}, route, worker=0,
                                              target=(3, 4))
        self.assertIsNone(candidate)
        self.assertEqual(report["reason"], "crop_not_mature")

        mature = m._new_plant("WHEAT", 27, 24)
        mature["yield_units"] = 1
        obs["farms"][0]["tiles"][4][3] = mature
        candidate, report = certify_candidate(m, obs, {}, route, worker=0,
                                              target=(3, 4))
        self.assertTrue(report["certified"])

    def test_actual_cow_harvest_can_finish_exactly_at_718(self):
        obs = observation(716, farmer=(3, 4))
        cow = m._new_animal("COW", 1)
        cow["yield_units"] = 1
        obs["farms"][0]["tiles"][4][3] = cow
        route = [row() for _ in range(720)]
        candidate, report = certify_candidate(m, obs, {}, route, worker=0,
                                              target=(3, 4))
        self.assertTrue(report["certified"])
        self.assertEqual(candidate.product, "MILK")
        self.assertEqual(candidate.terminal_step, 718)
        self.assertEqual(candidate.unit_actions,
                         (("HARVEST",), ("EAST",), ("DROP",)))

    def test_earlier_actor_cannot_consume_selected_harvest_source(self):
        obs = observation(712, farmer=(3, 4), hands=((3, 4),))
        wheat = m._new_plant("WHEAT", 25, 24)
        wheat["yield_units"] = 1
        obs["farms"][0]["tiles"][4][3] = wheat
        route = [row(hands=1) for _ in range(720)]
        route[712]["farmer"] = ["HARVEST"]

        candidate, report = certify_candidate(m, obs, {}, route, worker=1,
                                              target=(3, 4))
        self.assertIsNone(candidate)
        self.assertEqual(report["reason"], "other_actor_source_collision")
        self.assertEqual(report["conflict_step"], 712)
        self.assertEqual(report["conflict_worker"], 0)

        # Interpreter order is main farmer, then hands: the selected hand gets zero.
        day = obs["step"] // 24
        m._apply_unit_action(obs["farms"][0], obs["private"], 0, ["HARVEST"],
                             10, day, 24, 100)
        m._apply_unit_action(obs["farms"][0], obs["private"], 1, ["HARVEST"],
                             10, day, 24, 100)
        self.assertEqual(obs["private"]["inventories"][1], {})

    def test_later_actor_on_same_step_does_not_preempt_main_farmer(self):
        obs = observation(712, farmer=(3, 4), hands=((3, 4),))
        wheat = m._new_plant("WHEAT", 25, 24)
        wheat["yield_units"] = 1
        obs["farms"][0]["tiles"][4][3] = wheat
        route = [row(hands=1) for _ in range(720)]
        route[712]["hands"][0] = ["HARVEST"]

        candidate, report = certify_candidate(m, obs, {}, route, worker=0,
                                              target=(3, 4))
        self.assertTrue(report["certified"])
        self.assertEqual(candidate.unit_actions[0], ("HARVEST",))

    def test_other_actor_movement_is_replayed_before_source_check(self):
        obs = observation(712, farmer=(5, 4), hands=((4, 4),))
        wheat = m._new_plant("WHEAT", 25, 24)
        wheat["yield_units"] = 1
        obs["farms"][0]["tiles"][4][2] = wheat
        route = [row(hands=1) for _ in range(720)]
        route[712]["hands"][0] = ["WEST"]
        route[713]["hands"][0] = ["WEST"]
        route[714]["hands"][0] = ["HARVEST"]

        # Main farmer needs three WEST moves; hand 1 reaches and consumes the
        # target one step earlier than the selected worker's HARVEST at 715.
        candidate, report = certify_candidate(m, obs, {}, route, worker=0,
                                              target=(2, 4))
        self.assertIsNone(candidate)
        self.assertEqual(report["reason"], "other_actor_source_collision")
        self.assertEqual(report["conflict_step"], 714)

    def test_actual_decay_before_harvest_is_rejected(self):
        obs = observation(704, farmer=(4, 4))
        wheat = m._new_plant("WHEAT", 24, 24)
        wheat["yield_units"] = 1
        obs["farms"][0]["tiles"][4][3] = wheat
        route = [row() for _ in range(720)]

        candidate, report = certify_candidate(m, obs, {}, route, worker=0,
                                              target=(3, 4))
        self.assertIsNone(candidate)
        self.assertEqual(report["reason"], "source_decay_before_harvest")
        self.assertEqual(report["conflict_step"], 704)
        self.assertEqual(report["harvest_step"], 705)

        # Actual transition: move at 704, then decay; HARVEST at 705 is a no-op.
        day = obs["step"] // 24
        m._apply_unit_action(obs["farms"][0], obs["private"], 0, ["WEST"],
                             10, day, 24, 100)
        m._decay_plants(obs["farms"][0], 704)
        self.assertEqual(obs["farms"][0]["tiles"][4][3], {"kind": "WEED"})
        m._apply_unit_action(obs["farms"][0], obs["private"], 0, ["HARVEST"],
                             10, day, 24, 100)
        self.assertEqual(obs["private"]["inventories"][0], {})

    def test_decay_on_harvest_step_occurs_after_harvest(self):
        obs = observation(704, farmer=(3, 4))
        wheat = m._new_plant("WHEAT", 24, 24)
        wheat["yield_units"] = 1
        obs["farms"][0]["tiles"][4][3] = wheat
        route = [row() for _ in range(720)]

        candidate, report = certify_candidate(m, obs, {}, route, worker=0,
                                              target=(3, 4))
        self.assertTrue(report["certified"])
        self.assertEqual(report["harvest_step"], 704)

    def test_later_actor_pickup_siphons_candidate_drop_is_rejected(self):
        # Witness: at 718 both on shed-access; worker 0 carries WHEAT 1; hand 1 does PICKUP WHEAT 2;
        # certificate would DROP then SELL but actual order DROP then PICKUP empties shed before SELL.
        obs = observation(718, farmer=(4, 4), hands=((4, 4),),
                          shed={"WHEAT": 1},
                          inventories=[{"WHEAT": 1}, {}])
        route = [row(hands=1) for _ in range(720)]
        route[718]["hands"][0] = ["PICKUP", "WHEAT", 2]
        candidate, report = certify_candidate(m, obs, {}, route, worker=0,
                                              carried_product="WHEAT")
        self.assertIsNone(candidate)
        self.assertEqual(report["reason"], "other_actor_shed_collision")
        self.assertEqual(report["conflict_step"], 718)
        self.assertEqual(report["conflict_worker"], 1)


if __name__ == "__main__":
    unittest.main()
