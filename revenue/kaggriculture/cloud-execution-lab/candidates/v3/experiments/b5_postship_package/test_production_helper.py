# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("b5_postship_helper", HERE / "production_helper.py")
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def config(turns=24):
    return {"turnsPerDay": turns}


def observation(tile=None, fertilizer=1, step=120, hands=None, hand_inventories=None):
    hands = list(hands or [])
    inventories = [{"FERTILIZER": fertilizer}, *(hand_inventories or [])]
    return {
        "step": step,
        "player": 0,
        "farms": [{"tiles": [[tile]], "farmer": [0, 0], "hands": hands}],
        "private": {"inventories": inventories},
    }


class ProductionHelperTests(unittest.TestCase):
    def assertIdentity(self, obs, action, cfg=None):
        before = copy.deepcopy(action)
        result = m.apply_carrot_fertilizer(obs, config() if cfg is None else cfg, action)
        self.assertIs(result, action)
        self.assertEqual(action, before)

    def test_standard_config_eligible_literal_pass(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        obs = observation(carrot)
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "MILK", 2]]}
        before = copy.deepcopy(action)
        result = m.apply_carrot_fertilizer(obs, config(), action)
        self.assertEqual(action, before)
        self.assertEqual(result["farmer"], ["FERTILIZE"])
        self.assertEqual(result["hands"], [])
        self.assertEqual(result["market"], before["market"])

    def test_nonstandard_or_ambiguous_turns_per_day_is_identity(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        obs = observation(carrot)
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        for cfg in (
            None,
            {},
            {"turnsPerDay": 23},
            {"turnsPerDay": 25},
            {"turnsPerDay": True},
            {"turnsPerDay": 24.0},
            {"turnsPerDay": "24"},
        ):
            with self.subTest(cfg=cfg):
                self.assertIdentity(obs, action, cfg)

    def test_nonpass_noncarrot_zero_fertilizer_and_covered_are_identity(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        self.assertIdentity(
            observation({"kind": "PLANT", "crop": "WHEAT", "fertilized_until_day": -1}),
            action,
        )
        self.assertIdentity(
            observation({"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}),
            {"farmer": ["WATER"], "hands": [], "market": []},
        )
        self.assertIdentity(
            observation({"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}, fertilizer=0),
            action,
        )
        self.assertIdentity(
            observation({"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": 7}),
            action,
        )

    def test_same_tile_dedupe_one_replacement(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        obs = observation(carrot, hands=[[0, 0]], hand_inventories=[{"FERTILIZER": 1}])
        action = {"farmer": ["PASS"], "hands": [["PASS"]], "market": []}
        result = m.apply_carrot_fertilizer(obs, config(), action)
        self.assertEqual(result["farmer"], ["FERTILIZE"])
        self.assertEqual(result["hands"], [["PASS"]])

    def test_later_actor_poison_invalidates_whole_action(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        for bad_fertilizer in (True, -1, 1.0, "1", None):
            with self.subTest(fertilizer=bad_fertilizer):
                obs = observation(carrot, hands=[[0, 0]], hand_inventories=[{"FERTILIZER": bad_fertilizer}])
                self.assertIdentity(obs, {"farmer": ["PASS"], "hands": [["PASS"]], "market": []})

        obs = observation(carrot, hands=[[0, 0]], hand_inventories=[{}])
        self.assertIdentity(obs, {"farmer": ["PASS"], "hands": [["PASS", 1]], "market": []})

        bad_carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": None}
        obs = {
            "step": 120,
            "player": 0,
            "farms": [{
                "tiles": [[carrot, bad_carrot]],
                "farmer": [0, 0],
                "hands": [[1, 0]],
            }],
            "private": {"inventories": [{"FERTILIZER": 1}, {}]},
        }
        self.assertIdentity(obs, {"farmer": ["PASS"], "hands": [["PASS"]], "market": []})

    def test_malformed_actor_shapes_and_cardinality_are_identity(self):
        carrot = {"kind": "PLANT", "crop": "CARROT", "fertilized_until_day": -1}
        action = {"farmer": ["PASS"], "hands": [], "market": []}

        obs = observation(carrot)
        obs["player"] = True
        self.assertIdentity(obs, action)

        obs = observation(carrot)
        obs["step"] = 120.0
        self.assertIdentity(obs, action)

        obs = observation(carrot)
        obs["farms"][0]["farmer"] = [0.0, 0]
        self.assertIdentity(obs, action)

        obs = observation(carrot)
        obs["farms"][0]["hands"] = [[0, 0]]
        self.assertIdentity(obs, action)

        obs = observation(carrot)
        obs["private"]["inventories"] = [None]
        self.assertIdentity(obs, action)

    def test_donor_binding_is_explicit(self):
        self.assertEqual(m.DONOR_HEAD, "15e8367e4d3fff41e7e6eb2d088327f558764454")
        self.assertEqual(m.DONOR_BLOB, "4e4f9d490332f075cf50df595cb7a067d6236066")


if __name__ == "__main__":
    unittest.main()
