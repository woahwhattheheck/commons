# SPDX-License-Identifier: Apache-2.0
"""Pinned-engine predecessors plus conservative alternate-feed candidate tests."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EVALUATOR = ROOT / "reference/evaluator/evaluate.py"
ENGINE_DIR = ROOT / "reference/engine"
LOADER = ROOT / "reference/evaluator/loader.py"

candidate_spec = importlib.util.spec_from_file_location("v5_animal_cadence", HERE / "alternate_feed.py")
candidate = importlib.util.module_from_spec(candidate_spec)
candidate_spec.loader.exec_module(candidate)


class AlternateFeedCandidateTests(unittest.TestCase):
    def setUp(self):
        self.tile = {
            "kind": "PASTURE",
            "animal": "COW",
            "placed_day": 0,
            "yield_units": 0,
            "consecutive_unfed": 0,
            "fed_today": False,
            "cared_today": False,
            "fertilizer_available": False,
            "pending_care_bonus": 0,
        }
        tiles = [[None for _ in range(10)] for _ in range(10)]
        tiles[4][4] = self.tile
        self.farm = {"farmer": [0, 0], "hands": [[4, 4]], "tiles": tiles}
        self.obs = {
            "player": 0,
            "farms": [self.farm, {}],
            "private": {"inventories": [{}, {"WHEAT": 2}]},
        }
        self.selected = {
            "farmer": ["PASS"],
            "hands": [["FEED"]],
            "market": [["SELL", "EGG", 1]],
        }

    def apply(self):
        return candidate.apply_alternate_feed(self.obs, self.selected)

    def test_safe_zero_strike_feed_becomes_pass_without_other_edits(self):
        before = deepcopy((self.obs, self.selected))
        result, report = self.apply()
        self.assertEqual(result["hands"], [["PASS"]])
        self.assertEqual(result["farmer"], self.selected["farmer"])
        self.assertEqual(result["market"], self.selected["market"])
        self.assertTrue(report["changed"])
        self.assertEqual(report["wheat_saved"], 1)
        self.assertEqual(report["edits"][0]["animal"], "COW")
        self.assertEqual((self.obs, self.selected), before)

    def test_one_strike_leg_keeps_feed(self):
        self.tile["consecutive_unfed"] = 1
        result, report = self.apply()
        self.assertIs(result, self.selected)
        self.assertFalse(report["changed"])

    def test_no_actual_wheat_spend_keeps_feed(self):
        self.obs["private"]["inventories"][1].clear()
        result, report = self.apply()
        self.assertIs(result, self.selected)
        self.assertFalse(report["changed"])

    def test_current_or_pending_care_value_keeps_feed(self):
        for field, value in (("cared_today", True), ("pending_care_bonus", 1)):
            with self.subTest(field=field):
                self.tile["cared_today"] = False
                self.tile["pending_care_bonus"] = 0
                self.tile[field] = value
                result, report = self.apply()
                self.assertIs(result, self.selected)
                self.assertFalse(report["changed"])

    def test_same_tile_selected_care_keeps_feed(self):
        self.farm["farmer"] = [4, 4]
        self.selected["farmer"] = ["CARE"]
        result, report = self.apply()
        self.assertIs(result, self.selected)
        self.assertFalse(report["changed"])

    def test_malformed_public_identity_fails_closed(self):
        self.obs["player"] = True
        result, report = self.apply()
        self.assertIs(result, self.selected)
        self.assertEqual(report["reason"], "malformed_public_identity")


class PinnedEngineAnimalCadenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        evaluator_spec = importlib.util.spec_from_file_location("animal_cadence_evaluator", EVALUATOR)
        cls.ev = importlib.util.module_from_spec(evaluator_spec)
        evaluator_spec.loader.exec_module(cls.ev)
        cls.engine, cls.hashes = cls.ev.get_engine(ENGINE_DIR, LOADER)

    def goose(self):
        farm = self.engine._new_farm(10, 3000)
        farm["tiles"][0][0] = self.engine._new_animal("GOOSE", 0)
        return farm, farm["tiles"][0][0]

    def test_unfed_production_day_survives_and_still_produces(self):
        farm, tile = self.goose()
        self.engine._daily_refresh_animals(farm, 3)
        self.assertIs(farm["tiles"][0][0], tile)
        self.assertEqual(tile["consecutive_unfed"], 1)
        self.assertEqual(tile["yield_units"], 1)

    def test_second_consecutive_unfed_day_is_the_escape_boundary(self):
        farm, tile = self.goose()
        self.engine._daily_refresh_animals(farm, 3)
        self.assertIn("animal", farm["tiles"][0][0])
        self.engine._daily_refresh_animals(farm, 4)
        self.assertEqual(farm["tiles"][0][0], {"kind": "COOP"})

    def test_alternate_day_feed_preserves_daily_goose_base_yield(self):
        farm, tile = self.goose()
        self.engine._daily_refresh_animals(farm, 3)
        self.assertEqual((tile["consecutive_unfed"], tile["yield_units"]), (1, 1))
        tile["fed_today"] = True
        self.engine._daily_refresh_animals(farm, 4)
        self.assertEqual((tile["consecutive_unfed"], tile["yield_units"]), (0, 2))

    def test_surviving_animal_refreshes_fertilizer_every_day(self):
        farm, tile = self.goose()
        tile["fed_today"] = True
        self.engine._daily_refresh_animals(farm, 0)
        self.assertTrue(tile["fertilizer_available"])
        tile["fertilizer_available"] = False  # model a successful collection
        tile["fed_today"] = True
        self.engine._daily_refresh_animals(farm, 1)
        self.assertTrue(tile["fertilizer_available"])

    def test_fertilize_extends_bonus_window_but_does_not_mint_yield(self):
        farm = self.engine._new_farm(10, 3000)
        farm["farmer"] = [0, 0]
        farm["tiles"][0][0] = self.engine._new_plant("MELON", 0, 24)
        private = self.engine._new_private()
        private["inventories"][0]["FERTILIZER"] = 1
        tile = farm["tiles"][0][0]
        before = tile["yield_units"]
        self.engine._apply_unit_action(farm, private, 0, ["FERTILIZE"], 10, 1, 24)
        self.assertEqual(tile["yield_units"], before)
        self.assertEqual(tile["fertilized_until_day"], 3)
        self.assertNotIn("FERTILIZER", private["inventories"][0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
