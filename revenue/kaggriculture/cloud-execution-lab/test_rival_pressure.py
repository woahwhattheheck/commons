"""Regression tests for evidence-backed rival market pressure."""

from __future__ import annotations

import copy
import unittest

import scheduler as s


def _inventory(value=10000):
    return {item: value for item in s.PRODUCTS}


def _farm(tile=None, position=(0, 0), size=2):
    tiles = [[None for _ in range(size)] for _ in range(size)]
    if tile is not None:
        tiles[0][0] = copy.deepcopy(tile)
    return {
        "money": 3000,
        "farmer": list(position),
        "hands": [],
        "unlocked_quadrants": ["NW"],
        "hires_today": 0,
        "tiles": tiles,
    }


def _observation(step, *, rival_tile=None, rival_position=(0, 0),
                 inventory=None, shops=None):
    return {
        "step": step,
        "player": 0,
        "farms": [_farm(), _farm(rival_tile, rival_position)],
        "market": {
            "inventory": dict(inventory or _inventory()),
            "prices": _inventory(100),
        },
        "town": {"unlocked_shops": list(shops or [])},
    }


class RivalPressureTests(unittest.TestCase):
    def test_unharvested_standing_yield_is_not_assumed_to_be_a_sale(self):
        agent = s.SellScheduler()
        obs = _observation(
            10,
            rival_tile={"kind": "PLANT", "crop": "MELON", "yield_units": 6},
            rival_position=(1, 1),
        )
        self.assertEqual(
            agent.rival_pressure(obs, "MELON"),
            {
                "burst_quantity": 0,
                "window_quantity": 0,
                "market_flow_lower_bound": 0,
                "confirmed_harvest_units": 0,
            },
        )

    def test_worker_occupied_full_harvest_is_evidence_but_decay_is_not(self):
        harvested = s.SellScheduler()
        before = _observation(
            10,
            rival_tile={"kind": "PLANT", "crop": "TOMATO", "yield_units": 4},
            rival_position=(0, 0),
        )
        after = _observation(
            11,
            rival_tile={"kind": "PLANT", "crop": "TOMATO", "yield_units": 0},
            rival_position=(0, 0),
        )
        harvested.previous = copy.deepcopy(before)
        harvested.observe(after, {})
        self.assertEqual(harvested.observed_harvests["TOMATO"], [(11, 4)])
        self.assertEqual(harvested.rival_supply(after, "TOMATO"), 4)

        decayed = s.SellScheduler()
        before = _observation(
            10,
            rival_tile={"kind": "PLANT", "crop": "TOMATO", "yield_units": 4},
            rival_position=(1, 1),
        )
        after = _observation(
            11,
            rival_tile={"kind": "PLANT", "crop": "TOMATO", "yield_units": 3},
            rival_position=(1, 1),
        )
        decayed.previous = copy.deepcopy(before)
        decayed.observe(after, {})
        self.assertNotIn("TOMATO", decayed.observed_harvests)

    def test_public_market_delta_recovers_safe_rival_sale_lower_bound(self):
        agent = s.SellScheduler()
        shops = ["SMOOTHIE_SHOP"]
        before_inventory = _inventory()
        after_inventory = {
            item: before_inventory[item] - s.absorption(item, 4, shops, {})
            for item in s.PRODUCTS
        }
        after_inventory["MILK"] += 7  # Seven admitted units across both seats.

        before = _observation(4, inventory=before_inventory, shops=shops)
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "MILK", 6]],
        }
        shed = {item: 0 for item in s.PRODUCTS}
        shed["MILK"] = 3  # At most three of our six offered units can execute.
        agent.remember(before, action, shed)

        after = _observation(5, inventory=after_inventory, shops=shops)
        agent.observe(after, {})
        self.assertEqual(agent.previous_sale_caps["MILK"], 3)
        self.assertEqual(agent.observed_rival_sales["MILK"], [(5, 4)])
        self.assertEqual(
            agent.rival_pressure(after, "MILK")["market_flow_lower_bound"], 4
        )

    def test_pressure_separates_single_burst_from_horizon_volume(self):
        agent = s.SellScheduler()
        agent.observed_rival_sales["WOOL"] = [(8, 9), (10, 2), (12, 3)]
        agent.observed_harvests["WOOL"] = [(11, 4)]
        pressure = agent.rival_pressure(_observation(12), "WOOL")
        self.assertEqual(pressure["burst_quantity"], 9)
        self.assertEqual(pressure["window_quantity"], 14)

        # The oldest event drops out once it leaves the eight-step horizon.
        pressure = agent.rival_pressure(_observation(17), "WOOL")
        self.assertEqual(pressure["burst_quantity"], 4)
        self.assertEqual(pressure["window_quantity"], 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
