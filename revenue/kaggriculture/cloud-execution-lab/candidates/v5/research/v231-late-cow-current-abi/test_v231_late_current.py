# SPDX-License-Identifier: Apache-2.0
import copy
import unittest

from v231_late_current import (
    SUBMITTED_V31_ARCHIVE_SHA256,
    SUBMITTED_V31_ROUTER_GIT_BLOB,
    SUBMITTED_V31_ROUTER_SHA256,
    SUBMITTED_V31_SOURCE_COMMIT,
    V231LateCurrentABI,
)


def blank_tiles():
    tiles = [[{"kind": "EMPTY"} for _ in range(10)] for _ in range(10)]
    for x, y in [(0, 0), (1, 0), (2, 0), (3, 0)]:
        tiles[y][x] = {
            "kind": "PASTURE",
            "animal": "COW",
            "placed_day": 1,
            "yield_units": 0,
        }
    for x, y in [(0, 1), (1, 1)]:
        tiles[y][x] = {
            "kind": "PASTURE",
            "animal": "SHEEP",
            "placed_day": 1,
            "yield_units": 0,
        }
    return tiles


def observation(
    step=216,
    shed=None,
    inventories=None,
    shops=None,
    prices=None,
    farmer=(4, 4),
    hands=None,
    tiles=None,
):
    hands = list(hands or [])
    inv = inventories if inventories is not None else [{} for _ in range(1 + len(hands))]
    return {
        "step": step,
        "player": 0,
        "farms": [
            {
                "farmer": list(farmer),
                "hands": [list(p) for p in hands],
                "tiles": copy.deepcopy(tiles or blank_tiles()),
            }
        ],
        "private": {
            "shed": dict(shed or {"COW": 0, "SHEEP": 0, "GOOSE": 0, "MILK": 0}),
            "inventories": copy.deepcopy(inv),
        },
        "town": {
            "unlocked_shops": list(
                shops or ["PIZZA_SHOP", "ICE_CREAM_SHOP", "BAKERY"]
            )
        },
        "market": {"prices": dict(prices or {"MILK": 100, "WOOL": 90})},
    }


def selected(market=None, farmer=None, hands=None):
    return {
        "farmer": list(farmer or ["PASS"]),
        "hands": copy.deepcopy(hands or []),
        "market": copy.deepcopy(market or []),
    }


class TestV231LateCurrent(unittest.TestCase):
    def test_submitted_authority_is_pinned(self):
        self.assertEqual(
            SUBMITTED_V31_SOURCE_COMMIT,
            "a90d888f03987ef0b35cfd20ec3519c6144db08a",
        )
        self.assertEqual(
            SUBMITTED_V31_ROUTER_GIT_BLOB,
            "a3e2fe87c717d128e43c9b65bae2265f40d1d76d",
        )
        self.assertEqual(
            SUBMITTED_V31_ROUTER_SHA256,
            "41ea55c5f20c43cd58c5099fbadb212de62ec95a95dfc2e6e1e19c3d4d55b39a",
        )
        self.assertEqual(
            SUBMITTED_V31_ARCHIVE_SHA256,
            "5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361",
        )

    def test_off_is_identity_and_detached(self):
        arm = V231LateCurrentABI(enabled=False)
        action = selected([["BUY_ANIMAL", "SHEEP", 1]])
        out = arm.transform(observation(), action)
        self.assertEqual(out, action)
        self.assertIsNot(out, action)

    def test_exact_bool_required(self):
        with self.assertRaises(TypeError):
            V231LateCurrentABI(enabled=1)

    def test_late_window_converts_single_sheep_buy(self):
        arm = V231LateCurrentABI(enabled=True)
        action = selected([["BUY_ANIMAL", "SHEEP", 2]])
        out = arm.transform(observation(step=216), action)
        self.assertEqual(out["market"], [["BUY_ANIMAL", "COW", 2]])
        self.assertEqual(action["market"], [["BUY_ANIMAL", "SHEEP", 2]])

    def test_submitted_early_window_stays_off(self):
        arm = V231LateCurrentABI(enabled=True)
        action = selected([["BUY_ANIMAL", "SHEEP", 1]])
        out = arm.transform(observation(step=200), action)
        self.assertEqual(out, action)

    def test_late_gate_requires_milk_shop_and_price(self):
        for shops, prices in [
            (
                ["PIZZA_SHOP", "BAKERY", "PET_CAFE"],
                {"MILK": 100, "WOOL": 90},
            ),
            (
                ["PIZZA_SHOP", "ICE_CREAM_SHOP", "YARN_STORE"],
                {"MILK": 100, "WOOL": 90},
            ),
            (
                ["PIZZA_SHOP", "ICE_CREAM_SHOP", "BAKERY"],
                {"MILK": 89, "WOOL": 90},
            ),
        ]:
            with self.subTest(shops=shops, prices=prices):
                arm = V231LateCurrentABI(enabled=True)
                action = selected([["BUY_ANIMAL", "SHEEP", 1]])
                self.assertEqual(
                    arm.transform(observation(shops=shops, prices=prices), action),
                    action,
                )

    def test_requires_existing_four_cows_two_sheep_and_one_animal_order(self):
        tiles = blank_tiles()
        tiles[0][0] = {"kind": "PASTURE"}
        arm = V231LateCurrentABI(enabled=True)
        action = selected([["BUY_ANIMAL", "SHEEP", 1]])
        self.assertEqual(arm.transform(observation(tiles=tiles), action), action)

        arm = V231LateCurrentABI(enabled=True)
        action2 = selected(
            [["BUY_ANIMAL", "SHEEP", 1], ["BUY_ANIMAL", "GOOSE", 1]]
        )
        self.assertEqual(arm.transform(observation(), action2), action2)

    def test_existing_animal_cargo_or_stock_blocks_purchase(self):
        arm = V231LateCurrentABI(enabled=True)
        action = selected([["BUY_ANIMAL", "SHEEP", 1]])
        obs = observation(inventories=[{"COW": 1}])
        self.assertEqual(arm.transform(obs, action), action)

        arm = V231LateCurrentABI(enabled=True)
        obs2 = observation(
            shed={"COW": 1, "SHEEP": 0, "GOOSE": 0, "MILK": 0}
        )
        self.assertEqual(arm.transform(obs2, action), action)

    def test_confirmed_buy_redirects_sheep_pickup_to_cow(self):
        arm = V231LateCurrentABI(enabled=True)
        arm.transform(
            observation(step=216),
            selected([["BUY_ANIMAL", "SHEEP", 1]]),
        )
        obs = observation(
            step=217,
            shed={"COW": 1, "SHEEP": 1, "GOOSE": 0, "MILK": 0},
            farmer=(4, 4),
            inventories=[{}],
        )
        out = arm.transform(obs, selected(farmer=["PICKUP", "SHEEP", 1]))
        self.assertEqual(out["farmer"], ["PICKUP", "COW", 1])

    def test_pickup_then_place_redirect_tracks_confirmed_cow_site(self):
        arm = V231LateCurrentABI(enabled=True)
        arm.transform(
            observation(step=216),
            selected([["BUY_ANIMAL", "SHEEP", 1]]),
        )
        arm.transform(
            observation(
                step=217,
                shed={"COW": 1, "SHEEP": 1, "GOOSE": 0, "MILK": 0},
                farmer=(4, 4),
                inventories=[{}],
            ),
            selected(farmer=["PICKUP", "SHEEP", 1]),
        )
        tiles = blank_tiles()
        tiles[4][4] = {"kind": "PASTURE"}
        out = arm.transform(
            observation(
                step=218,
                shed={"COW": 0, "SHEEP": 1, "GOOSE": 0, "MILK": 0},
                farmer=(4, 4),
                inventories=[{"COW": 1}],
                tiles=tiles,
            ),
            selected(farmer=["PLACE", "SHEEP"]),
        )
        self.assertEqual(out["farmer"], ["PLACE", "COW"])
        tiles2 = copy.deepcopy(tiles)
        tiles2[4][4] = {
            "kind": "PASTURE",
            "animal": "COW",
            "placed_day": 9,
            "yield_units": 3,
        }
        arm.transform(
            observation(
                step=219,
                shed={"COW": 0, "SHEEP": 0, "GOOSE": 0, "MILK": 0},
                farmer=(4, 4),
                inventories=[{}],
                tiles=tiles2,
            ),
            selected(),
        )
        self.assertEqual(arm._states[0]["placed"], 1)

    def _credit_arm(self):
        arm = V231LateCurrentABI(enabled=True)
        arm._states[0] = {
            "last": 219,
            "confirmed": 1,
            "reserved": 0,
            "pending_buy": None,
            "carrying": {},
            "pending_places": [],
            "sites": {(4, 4): 9},
            "milk_credit": 0,
            "requested": 1,
            "failed_purchase_units": 0,
            "picked": 1,
            "placed": 1,
            "failed_placements": 0,
            "extra_milk_harvested": 0,
            "extra_milk_sale_requests": 0,
        }
        return arm

    def test_harvest_credit_only_expands_existing_milk_sale(self):
        arm = self._credit_arm()
        tiles = blank_tiles()
        tiles[4][4] = {
            "kind": "PASTURE",
            "animal": "COW",
            "placed_day": 9,
            "yield_units": 3,
        }
        obs = observation(
            step=220,
            shed={"COW": 0, "SHEEP": 0, "GOOSE": 0, "MILK": 8},
            farmer=(4, 4),
            inventories=[{}],
            tiles=tiles,
        )
        out = arm.transform(
            obs,
            selected(market=[["SELL", "MILK", 2]], farmer=["HARVEST"]),
        )
        self.assertEqual(out["market"], [["SELL", "MILK", 5]])
        self.assertEqual(arm._states[0]["milk_credit"], 0)

    def test_no_new_milk_sale_row_is_invented(self):
        arm = self._credit_arm()
        tiles = blank_tiles()
        tiles[4][4] = {
            "kind": "PASTURE",
            "animal": "COW",
            "placed_day": 9,
            "yield_units": 3,
        }
        obs = observation(
            step=220,
            shed={"COW": 0, "SHEEP": 0, "GOOSE": 0, "MILK": 8},
            farmer=(4, 4),
            inventories=[{}],
            tiles=tiles,
        )
        out = arm.transform(obs, selected(farmer=["HARVEST"]))
        self.assertEqual(out["market"], [])
        self.assertEqual(arm._states[0]["milk_credit"], 3)

    def test_malformed_current_envelope_fails_identity_without_throw(self):
        arm = V231LateCurrentABI(enabled=True)
        action = selected([["BUY_ANIMAL", "SHEEP", 1]])
        obs = observation()
        obs["private"]["inventories"] = []
        self.assertEqual(arm.transform(obs, action), action)

        bad_action = copy.deepcopy(action)
        bad_action["hands"] = 7
        self.assertEqual(arm.transform(observation(), bad_action), bad_action)


if __name__ == "__main__":
    unittest.main()
