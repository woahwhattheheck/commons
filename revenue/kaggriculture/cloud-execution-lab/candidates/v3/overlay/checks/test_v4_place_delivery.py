# SPDX-License-Identifier: Apache-2.0
"""Focused checks for V4 ``r04_place_delivery``.

Run in a materialised candidate package:

    python -B -m unittest -v checks/test_v4_place_delivery.py
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import r04_full_router as r04  # noqa: E402
import r04_place_delivery as lane  # noqa: E402
from titan_runtime import Features, TitanAgent  # noqa: E402

CONFIG = {"episodeSteps": 720, "turnsPerDay": 24, "boardSize": 10,
          "shedCapacity": 100, "maxMarketOrdersPerTurn": 10,
          "farmHandCostMult": 1}


def observation(step=718, shed=None, inventories=None, prices=None):
    tiles = [["LOCKED"] * 10 for _ in range(10)]
    for y in range(3, 7):
        for x in range(3, 7):
            tiles[y][x] = {"kind": "SOIL"}
    farm = {"tiles": tiles, "farmer": [4, 4], "hands": [[5, 4]],
            "money": 1000, "unlocked_quadrants": ["NW"], "hires_today": 0}
    market_prices = {product: 10 for product in r04.PRODUCTS}
    market_prices.update(prices or {})
    return {"step": step, "day": step // 24, "hour": step % 24, "player": 0,
            "farms": [farm, copy.deepcopy(farm)],
            "private": {"inventories": inventories or [{}, {}],
                        "shed": shed or {}},
            "market": {"prices": market_prices},
            "town": {"unlocked_shops": ["BAKERY", "YARN_STORE"]}}


def action(farmer=None, hands=None, market=None):
    return {"farmer": farmer or ["PASS"], "hands": hands or [["PASS"]],
            "market": market or []}


class PlaceDelivery(unittest.TestCase):
    def tearDown(self):
        r04.PLACE_DELIVERY = False

    def test_key_ships_off_and_features_accept_it(self):
        data = json.loads((ROOT / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
        self.assertIs(data["r04_place_delivery"], False)
        self.assertIs(Features(**data).r04_place_delivery, False)

    def test_disabled_is_exact_parent_object(self):
        parent = action(["DROP"], [["DROP"]], [["SELL", "WHEAT", 1]])
        obs = observation(shed={"WHEAT": 98}, inventories=[{"CARROT": 5}, {"WOOL": 5}])
        self.assertIs(lane.apply_place_delivery(obs, parent, enabled=False), parent)

    def test_nonterminal_is_exact_parent_object(self):
        parent = action(["DROP"], [["DROP"]])
        obs = observation(step=717, shed={"WHEAT": 98},
                          inventories=[{"CARROT": 5}, {"WOOL": 5}])
        self.assertIs(lane.apply_place_delivery(obs, parent, enabled=True), parent)

    def test_terminal_without_adjacent_drop_is_exact_parent_object(self):
        parent = action(["PASS"], [["PASS"]], [["SELL", "WHEAT", 98]])
        obs = observation(shed={"WHEAT": 98}, inventories=[{"CARROT": 5}, {"WOOL": 5}])
        self.assertIs(lane.apply_place_delivery(obs, parent, enabled=True), parent)

    def test_roomy_shed_keeps_drop_exact_parent_object(self):
        parent = action(["DROP"], [["DROP"]], [["SELL", "WHEAT", 90]])
        obs = observation(shed={"WHEAT": 90},
                          inventories=[{"CARROT": 5}, {"WOOL": 5}])
        self.assertIs(lane.apply_place_delivery(obs, parent, enabled=True), parent)

    def test_roomy_shed_preserves_multi_product_drop(self):
        parent = action(["DROP"], [["PASS"]])
        obs = observation(shed={"WHEAT": 90},
                          inventories=[{"CARROT": 5, "WOOL": 5}, {}])
        self.assertIs(lane.apply_place_delivery(obs, parent, enabled=True), parent)

    def test_overflow_multi_product_drop_fails_closed_to_parent(self):
        # Baseline farmer DROP admits both products and fills all ten free shed
        # slots before the hand's final unit is discarded. A one-product PLACE
        # rewrite would otherwise underfill the shed and lose terminal value.
        parent = action(["DROP"], [["DROP"]])
        obs = observation(
            shed={"WHEAT": 90},
            inventories=[{"WOOL": 5, "CARROT": 5}, {"WHEAT": 1}],
            prices={"WOOL": 100, "CARROT": 10, "WHEAT": 5},
        )
        self.assertIs(lane.apply_place_delivery(obs, parent, enabled=True), parent)

    def test_overflow_becomes_bounded_place_and_preserves_excess_cargo(self):
        parent = action(["DROP"], [["PASS"]])
        obs = observation(shed={"WHEAT": 98}, inventories=[{"CARROT": 5}, {}],
                          prices={"CARROT": 30})
        out = lane.apply_place_delivery(obs, parent, enabled=True)
        self.assertEqual(out["farmer"], ["PLACE", "CARROT", 2])
        self.assertNotIn(["DROP"], [out["farmer"], *out["hands"]])
        self.assertIn(["SELL", "CARROT", 2], out["market"])
        self.assertIn(["SELL", "WHEAT", 98], out["market"])
        self.assertEqual(sum(row[2] for row in out["market"]), 100)

    def test_animal_cargo_counts_toward_overflow_without_product_price(self):
        parent = action(["DROP"], [["PASS"]])
        obs = observation(shed={"WHEAT": 98}, inventories=[{"GOOSE": 3}, {}])
        out = lane.apply_place_delivery(obs, parent, enabled=True)
        self.assertEqual(out["farmer"], ["PASS"])
        self.assertNotIn(["DROP"], [out["farmer"], *out["hands"]])
        self.assertEqual(out["market"], [["SELL", "WHEAT", 98]])

    def test_full_shed_never_drops_worker_cargo(self):
        parent = action(["DROP"], [["PASS"]])
        obs = observation(shed={"WHEAT": 100}, inventories=[{"CARROT": 5}, {}])
        out = lane.apply_place_delivery(obs, parent, enabled=True)
        self.assertEqual(out["farmer"], ["PASS"])
        self.assertNotIn(["DROP"], [out["farmer"], *out["hands"]])
        self.assertEqual(out["market"], [["SELL", "WHEAT", 100]])

    def test_capacity_goes_to_higher_value_worker(self):
        parent = action(["DROP"], [["DROP"]])
        obs = observation(shed={"WHEAT": 98},
                          inventories=[{"CARROT": 5}, {"WOOL": 5}],
                          prices={"CARROT": 5, "WOOL": 100})
        out = lane.apply_place_delivery(obs, parent, enabled=True)
        self.assertEqual(out["farmer"], ["PASS"])
        self.assertEqual(out["hands"], [["PLACE", "WOOL", 2]])
        self.assertIn(["SELL", "WOOL", 2], out["market"])
        self.assertNotIn(["DROP"], [out["farmer"], *out["hands"]])

    def test_string_step_fails_closed_to_exact_parent(self):
        parent = action(["DROP"], [["PASS"]])
        obs = observation(shed={"WHEAT": 98}, inventories=[{"CARROT": 5}, {}])
        obs["step"] = "718"
        self.assertIs(lane.apply_place_delivery(obs, parent, enabled=True), parent)

    def test_malformed_shed_quantity_fails_closed_to_exact_parent(self):
        parent = action(["DROP"], [["PASS"]])
        obs = observation(shed={"WHEAT": 98}, inventories=[{"CARROT": 5}, {}])
        obs["private"]["shed"]["WHEAT"] = "98"
        self.assertIs(lane.apply_place_delivery(obs, parent, enabled=True), parent)

    def test_malformed_touched_price_fails_closed_to_exact_parent(self):
        parent = action(["DROP"], [["PASS"]])
        obs = observation(shed={"WHEAT": 98}, inventories=[{"CARROT": 5}, {}],
                          prices={"CARROT": "30"})
        self.assertIs(lane.apply_place_delivery(obs, parent, enabled=True), parent)

    def test_malformed_shed_product_price_fails_closed_to_exact_parent(self):
        parent = action(["DROP"], [["PASS"]])
        obs = observation(shed={"WHEAT": 98}, inventories=[{"CARROT": 5}, {}],
                          prices={"WHEAT": "10"})
        self.assertIs(lane.apply_place_delivery(obs, parent, enabled=True), parent)

    def test_malformed_worker_position_fails_closed_to_exact_parent(self):
        parent = action(["DROP"], [["PASS"]])
        obs = observation(shed={"WHEAT": 98}, inventories=[{"CARROT": 5}, {}])
        obs["farms"][0]["farmer"] = [4]
        self.assertIs(lane.apply_place_delivery(obs, parent, enabled=True), parent)

    def test_malformed_board_shape_fails_closed_to_exact_parent(self):
        parent = action(["DROP"], [["PASS"]])
        obs = observation(shed={"WHEAT": 98}, inventories=[{"CARROT": 5}, {}])
        obs["farms"][0]["tiles"] = [["LOCKED"] * 2 for _ in range(2)]
        obs["farms"][0]["farmer"] = [0, 0]
        obs["farms"][0]["hands"] = [[1, 0]]
        self.assertIs(lane.apply_place_delivery(obs, parent, enabled=True), parent)

    def test_truncated_worker_positions_fail_closed_to_exact_parent(self):
        parent = action(["DROP"], [["DROP"]])
        obs = observation(shed={"WHEAT": 98},
                          inventories=[{"CARROT": 5}, {"WOOL": 5}])
        obs["farms"][0]["hands"] = []
        self.assertIs(lane.apply_place_delivery(obs, parent, enabled=True), parent)

    def test_truncated_worker_inventories_fail_closed_to_exact_parent(self):
        parent = action(["DROP"], [["DROP"]])
        obs = observation(shed={"WHEAT": 98}, inventories=[{"CARROT": 5}])
        self.assertIs(lane.apply_place_delivery(obs, parent, enabled=True), parent)

    def test_malformed_action_hands_fail_closed_to_exact_parent(self):
        parent = action(["DROP"], 7)
        obs = observation(shed={"WHEAT": 98}, inventories=[{"CARROT": 5}, {}])
        self.assertIs(lane.apply_place_delivery(obs, parent, enabled=True), parent)

    def test_missing_action_actor_fields_fail_closed_to_exact_parent(self):
        obs = observation(shed={"WHEAT": 98}, inventories=[{"CARROT": 5}, {}])
        missing_hands = {"farmer": ["DROP"], "market": []}
        self.assertIs(lane.apply_place_delivery(obs, missing_hands, enabled=True), missing_hands)
        missing_farmer = {"hands": [["DROP"]], "market": []}
        self.assertIs(lane.apply_place_delivery(obs, missing_farmer, enabled=True), missing_farmer)

    def test_parent_actor_prefix_fails_closed_to_exact_parent(self):
        parent = {"farmer": ["DROP"], "hands": [], "market": []}
        obs = observation(shed={"WHEAT": 98},
                          inventories=[{"CARROT": 5}, {"WOOL": 5}])
        self.assertIs(lane.apply_place_delivery(obs, parent, enabled=True), parent)

    def test_farm_view_failure_fails_closed_to_exact_parent(self):
        parent = action(["DROP"], [["PASS"]])
        obs = observation(shed={"WHEAT": 98}, inventories=[{"CARROT": 5}, {}])
        with mock.patch.object(r04, "FarmView", side_effect=ValueError("bad observation")):
            self.assertIs(lane.apply_place_delivery(obs, parent, enabled=True), parent)

    def test_install_and_titan_diagnostics_carry_key(self):
        r04.install(None, 8, 0, False, False, place_delivery=True)
        self.assertIs(r04.PLACE_DELIVERY, True)
        r04.install(None, 8, 0, False, False, place_delivery=False)
        self.assertIs(r04.PLACE_DELIVERY, False)

        agent = TitanAgent(Features(r04_sale_window=True, r04_place_delivery=True))
        agent.act(observation(step=0, inventories=[{}, {}]), dict(CONFIG))
        self.assertIs(r04.PLACE_DELIVERY, True)
        self.assertIs(agent.diagnostics["place_delivery"], True)


if __name__ == "__main__":
    unittest.main()
