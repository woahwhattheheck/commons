# SPDX-License-Identifier: Apache-2.0
"""Focused checks for V4 ``r04_bakery_yarn_route``.

Run in a materialised candidate package:

    python -B -m unittest -v checks/test_v4_bakery_yarn_route.py
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import r04_full_router as r04  # noqa: E402
from titan_runtime import Features, TitanAgent  # noqa: E402

CONFIG = {
    "episodeSteps": 720,
    "turnsPerDay": 24,
    "boardSize": 10,
    "townShopUnlockInterval": 3,
    "shedCapacity": 100,
    "maxMarketOrdersPerTurn": 10,
    "farmHandCostMult": 1,
    "marketParams": {},
}


class Struct:
    def __init__(self, values):
        self.__dict__.update(values)


def observation(step=144, shops=("BAKERY", "YARN_STORE"), player=0):
    tiles = [["LOCKED"] * 10 for _ in range(10)]
    for y in range(3, 7):
        for x in range(3, 7):
            tiles[y][x] = {"kind": "SOIL"}
    farm = {"tiles": tiles, "farmer": [4, 4], "hands": [], "money": 1000,
            "unlocked_quadrants": ["NW"], "hires_today": 0}
    return {"step": step, "day": step // 24, "hour": step % 24, "player": player,
            "farms": [farm, copy.deepcopy(farm)],
            "private": {"inventories": [{}], "shed": {"WHEAT": 5}},
            "market": {"prices": {product: 10 for product in r04.PRODUCTS}},
            "town": {"unlocked_shops": list(shops)}}


class BakeryYarnRoute(unittest.TestCase):
    def setUp(self):
        r04.BAKERY_YARN_ROUTE = False
        r04._POLICY = None

    def tearDown(self):
        r04.BAKERY_YARN_ROUTE = False
        r04._POLICY = None

    def _plan(self, *, enabled=True, shops=("BAKERY", "YARN_STORE"), config=CONFIG):
        r04.BAKERY_YARN_ROUTE = enabled
        policy = r04.Policy(ROOT)
        policy.act(observation(shops=shops), config)
        return policy.players[0].plan

    def test_key_ships_off_and_features_accept_it(self):
        data = json.loads((ROOT / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
        self.assertIs(data["r04_bakery_yarn_route"], False)
        self.assertIs(Features(**data).r04_bakery_yarn_route, False)

    def test_published_route_table_is_not_mutated(self):
        self.assertEqual(r04.SHOP_PLANS[("BAKERY", "YARN_STORE")], 3)

    def test_disabled_keeps_published_plan_three_without_configuration(self):
        self.assertEqual(self._plan(enabled=False, config=None), 3)

    def test_enabled_selects_existing_plan_nine_on_exact_standard_contract(self):
        self.assertEqual(self._plan(), 9)
        self.assertLess(9, len(r04.Policy(ROOT).tapes))

    def test_attribute_configuration_is_supported(self):
        self.assertEqual(self._plan(config=Struct(dict(CONFIG))), 9)

    def test_enabled_does_not_touch_neighboring_or_reversed_pairs(self):
        self.assertEqual(self._plan(shops=("PIZZA_SHOP", "YARN_STORE")),
                         r04.SHOP_PLANS[("PIZZA_SHOP", "YARN_STORE")])
        self.assertEqual(self._plan(shops=("YARN_STORE", "BAKERY")),
                         r04.SHOP_PLANS[("YARN_STORE", "BAKERY")])

    def test_full_shop_list_must_be_exact_not_matching_prefix(self):
        self.assertEqual(self._plan(shops=("BAKERY", "YARN_STORE", "PIZZA_SHOP")), 3)

    def test_missing_configuration_fails_closed_to_published_route(self):
        self.assertEqual(self._plan(config=None), 3)

    def test_nonstandard_day_or_unlock_cadence_fails_closed(self):
        for field, value in (("turnsPerDay", 12), ("townShopUnlockInterval", 2),
                             ("episodeSteps", 719), ("boardSize", 9),
                             ("shedCapacity", 101), ("maxMarketOrdersPerTurn", 9)):
            with self.subTest(field=field):
                config = dict(CONFIG)
                config[field] = value
                self.assertEqual(self._plan(config=config), 3)

    def test_bool_scalar_alias_fails_closed(self):
        config = dict(CONFIG)
        config["turnsPerDay"] = True
        self.assertEqual(self._plan(config=config), 3)

    def test_custom_market_params_fail_closed(self):
        config = dict(CONFIG)
        config["marketParams"] = {"priceScale": 2}
        self.assertEqual(self._plan(config=config), 3)

    def test_install_and_titan_runtime_forward_configuration(self):
        r04.install(bakery_yarn_route=True)
        self.assertIs(r04.BAKERY_YARN_ROUTE, True)
        agent = TitanAgent(Features(r04_sale_window=True, r04_bakery_yarn_route=True))
        agent.act(observation(), dict(CONFIG))
        self.assertIs(r04.BAKERY_YARN_ROUTE, True)
        self.assertIs(agent.diagnostics["bakery_yarn_route"], True)
        self.assertEqual(r04._POLICY.players[0].plan, 9)

        r04.install(bakery_yarn_route=False)
        self.assertIs(r04.BAKERY_YARN_ROUTE, False)


if __name__ == "__main__":
    unittest.main()
