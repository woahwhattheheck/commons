# SPDX-License-Identifier: Apache-2.0
"""P21 contracts against the repository's extracted Kaggriculture mechanics."""
from copy import deepcopy
import unittest

import mechanics as m
from terminal_route_value import certify_candidate


def row(hands=0, market=None):
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in range(hands)],
            "market": [] if market is None else deepcopy(market)}


def observation(step, *, farmer=(4, 4), shed=None, inventories=None):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    farm = {"farmer": list(farmer), "hands": [], "money": 1000,
            "hires_today": 0, "unlocked_quadrants": ["NW"], "tiles": tiles}
    rival = {"farmer": [4, 4], "hands": [], "money": 1000,
             "hires_today": 0, "unlocked_quadrants": ["NW"],
             "tiles": [[None for _ in range(10)] for _ in range(10)]}
    private = {"shed": {} if shed is None else deepcopy(shed),
               "inventories": [{}] if inventories is None else deepcopy(inventories),
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


if __name__ == "__main__":
    unittest.main()
