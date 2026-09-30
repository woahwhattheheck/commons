# SPDX-License-Identifier: Apache-2.0
"""Focused checks for V4 ``r04_dead_feed_care``.

Run in a materialised candidate package:

    python -B -m unittest -v checks/test_v4_dead_feed_care.py
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

import r04_dead_feed_care as lane  # noqa: E402
import r04_full_router as r04  # noqa: E402
from titan_runtime import Features, TitanAgent  # noqa: E402

CONFIG = {"episodeSteps": 720, "turnsPerDay": 24, "boardSize": 10,
          "shedCapacity": 100, "maxMarketOrdersPerTurn": 10,
          "farmHandCostMult": 1}


class StructConfig:
    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)


def animal_tile(species="GOOSE", *, fed=True, cared=False, placed_day=0):
    return {"kind": "COOP" if species == "GOOSE" else "PASTURE",
            "animal": species, "placed_day": placed_day, "yield_units": 1,
            "consecutive_unfed": 0, "fed_today": fed, "cared_today": cared,
            "fertilizer_available": True, "pending_care_bonus": 0}


def observation(*, step=120, player=0, tile=None, farmer=(4, 4), hands=((5, 4),)):
    tiles = [["LOCKED"] * 10 for _ in range(10)]
    tiles[4][4] = tile if tile is not None else animal_tile()
    farm = {"tiles": tiles, "farmer": list(farmer), "hands": [list(p) for p in hands],
            "money": 1000, "unlocked_quadrants": ["NW"], "hires_today": 0}
    prices = {product: 10 for product in r04.PRODUCTS}
    return {"step": step, "day": step // 24, "hour": step % 24, "player": player,
            "farms": [farm, copy.deepcopy(farm)],
            "private": {"inventories": [{}, {}], "shed": {}},
            "market": {"prices": prices},
            "town": {"unlocked_shops": ["BAKERY", "YARN_STORE"]}}


def action(*, farmer=None, hands=None, market=None):
    return {"farmer": ["FEED"] if farmer is None else farmer,
            "hands": [["PASS"]] if hands is None else hands,
            "market": [] if market is None else market}


class DeadFeedCare(unittest.TestCase):
    def tearDown(self):
        r04.DEAD_FEED_CARE = False

    def test_key_ships_off_and_features_accept_it(self):
        data = json.loads((ROOT / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
        self.assertIs(data["r04_dead_feed_care"], False)
        self.assertIs(Features(**data).r04_dead_feed_care, False)

    def test_disabled_is_exact_parent_object(self):
        parent = action()
        self.assertIs(lane.apply_dead_feed_care(
            parent, observation(), dict(CONFIG), enabled=False), parent)

    def test_already_fed_uncared_animal_becomes_care(self):
        for species in ("GOOSE", "COW", "SHEEP"):
            with self.subTest(species=species):
                parent = action(market=[["SELL", "WOOL", 1]])
                out = lane.apply_dead_feed_care(
                    parent, observation(tile=animal_tile(species)), dict(CONFIG), enabled=True)
                self.assertIsNot(out, parent)
                self.assertEqual(out["farmer"], ["CARE"])
                self.assertEqual(out["hands"], [["PASS"]])
                self.assertEqual(out["market"], [["SELL", "WOOL", 1]])
                self.assertEqual(parent["farmer"], ["FEED"])

    def test_struct_configuration_is_supported(self):
        parent = action()
        out = lane.apply_dead_feed_care(
            parent, observation(), StructConfig(CONFIG), enabled=True)
        self.assertEqual(out["farmer"], ["CARE"])

    def test_not_fed_is_exact_parent_object(self):
        parent = action()
        self.assertIs(lane.apply_dead_feed_care(
            parent, observation(tile=animal_tile(fed=False)), dict(CONFIG), enabled=True), parent)

    def test_already_cared_is_exact_parent_object(self):
        parent = action()
        self.assertIs(lane.apply_dead_feed_care(
            parent, observation(tile=animal_tile(cared=True)), dict(CONFIG), enabled=True), parent)

    def test_non_animal_is_exact_parent_object(self):
        parent = action()
        self.assertIs(lane.apply_dead_feed_care(
            parent, observation(tile={"kind": "PLANT", "crop": "WHEAT"}),
            dict(CONFIG), enabled=True), parent)

    def test_only_literal_feed_matches(self):
        parent = action(farmer=["FEED", "WHEAT"])
        self.assertIs(lane.apply_dead_feed_care(
            parent, observation(), dict(CONFIG), enabled=True), parent)

    def test_nonstandard_configuration_fails_closed(self):
        parent = action()
        bad = dict(CONFIG)
        bad["shedCapacity"] = 99
        self.assertIs(lane.apply_dead_feed_care(
            parent, observation(), bad, enabled=True), parent)

    def test_nonstandard_episode_steps_fails_closed(self):
        parent = action()
        for episode_steps in (696, 721, True):
            with self.subTest(episode_steps=episode_steps):
                bad = dict(CONFIG)
                bad["episodeSteps"] = episode_steps
                self.assertIs(lane.apply_dead_feed_care(
                    parent, observation(), bad, enabled=True), parent)

    def test_missing_episode_steps_fails_closed(self):
        parent = action()
        bad = dict(CONFIG)
        del bad["episodeSteps"]
        self.assertIs(lane.apply_dead_feed_care(
            parent, observation(), bad, enabled=True), parent)

    def test_bool_player_fails_closed(self):
        parent = action()
        self.assertIs(lane.apply_dead_feed_care(
            parent, observation(player=True), dict(CONFIG), enabled=True), parent)

    def test_action_actor_cardinality_mismatch_fails_closed(self):
        parent = action(hands=[])
        self.assertIs(lane.apply_dead_feed_care(
            parent, observation(), dict(CONFIG), enabled=True), parent)

    def test_duplicate_candidate_site_fails_closed(self):
        parent = action(hands=[["FEED"]])
        obs = observation(hands=((4, 4),))
        self.assertIs(lane.apply_dead_feed_care(
            parent, obs, dict(CONFIG), enabled=True), parent)

    def test_malformed_animal_state_fails_closed(self):
        parent = action()
        tile = animal_tile()
        tile["fed_today"] = 1
        self.assertIs(lane.apply_dead_feed_care(
            parent, observation(tile=tile), dict(CONFIG), enabled=True), parent)

    def test_unreachable_animal_state_fails_closed(self):
        parent = action()
        cases = (
            ("GOOSE", "yield_units", 5),
            ("COW", "yield_units", 7),
            ("SHEEP", "yield_units", 7),
            ("GOOSE", "consecutive_unfed", 2),
            ("GOOSE", "pending_care_bonus", 2),
            ("COW", "pending_care_bonus", 3),
            ("SHEEP", "pending_care_bonus", 4),
        )
        for species, field, value in cases:
            with self.subTest(species=species, field=field, value=value):
                tile = animal_tile(species)
                tile[field] = value
                self.assertIs(lane.apply_dead_feed_care(
                    parent, observation(tile=tile), dict(CONFIG), enabled=True), parent)

    def test_unhashable_animal_state_fails_closed(self):
        parent = action()
        tile = animal_tile()
        tile["animal"] = []
        self.assertIs(lane.apply_dead_feed_care(
            parent, observation(tile=tile), dict(CONFIG), enabled=True), parent)

    def test_install_and_titan_diagnostics_carry_key(self):
        r04.install(dead_feed_care=True)
        self.assertIs(r04.DEAD_FEED_CARE, True)
        r04.install(dead_feed_care=False)
        self.assertIs(r04.DEAD_FEED_CARE, False)

        agent = TitanAgent(Features(r04_sale_window=True, r04_dead_feed_care=True))
        agent.act(observation(step=0), dict(CONFIG))
        self.assertIs(r04.DEAD_FEED_CARE, True)
        self.assertIs(agent.diagnostics["dead_feed_care"], True)


if __name__ == "__main__":
    unittest.main()
