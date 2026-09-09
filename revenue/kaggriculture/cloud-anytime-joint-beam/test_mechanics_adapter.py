# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import importlib.util
import os
from pathlib import Path
import unittest

from joint_action_beam import BeamConfig, propose_worker_action, search_joint_actions
from mechanics_adapter import (
    MechanicsContext,
    ScoreContext,
    bounded_worker_candidates,
    mechanics_scorer,
    mechanics_transition,
    score_components,
)

HERE = Path(__file__).resolve().parent
MECHANICS_PATH = Path(os.environ.get(
    "S01_MECHANICS",
    HERE.parent / "cloud-execution-lab" / "mechanics.py",
))


def load_mechanics():
    spec = importlib.util.spec_from_file_location("s01_official_mechanics", MECHANICS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def fixture(workers=2):
    board = 10
    pos = [1, 1]
    return {
        "farm": {
            "farmer": list(pos),
            "hands": [list(pos) for _ in range(max(0, workers - 1))],
            "tiles": [[None for _ in range(board)] for _ in range(board)],
            "money": 500,
        },
        "private": {
            "shed": {},
            "seeds": {"WHEAT": 1},
            "inventories": [{} for _ in range(workers)],
        },
        "market": {"inventory": {item: 10000 for item in (
            "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
            "EGG", "MILK", "WOOL", "FERTILIZER")}},
    }


class OfficialMechanicsAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_mechanics()
        cls.ctx = MechanicsContext(board_size=10, day=0, turns_per_day=24)
        cls.transition = staticmethod(mechanics_transition(cls.m, cls.ctx))
        cls.score = staticmethod(mechanics_scorer(cls.m))

    def test_exact_plant_consumes_shared_seed_and_second_conflict_prunes(self):
        initial = fixture(2)
        first = self.transition(initial, 0, ["PLANT", "WHEAT"])
        self.assertIsNotNone(first)
        self.assertEqual(0, first["private"]["seeds"]["WHEAT"])
        self.assertIsNone(self.transition(first, 1, ["PLANT", "WHEAT"]))
        self.assertEqual(1, initial["private"]["seeds"]["WHEAT"])
        self.assertIsNone(initial["farm"]["tiles"][1][1])

    def test_beam_prunes_exact_shared_resource_conflict(self):
        canonical = (["PASS"], ["PASS"])
        result = search_joint_actions(
            fixture(2), canonical,
            lambda state, idx, base: (["PLANT", "WHEAT"], ["PASS"]),
            self.transition, self.score,
            config=BeamConfig(width=24, depth=4, budget_ns=35_000_000),
        )
        self.assertIn(result.reason, {"complete", "deadline-during-search", "deadline-during-finalization"})
        if result.complete:
            self.assertEqual(1, sum(action == ["PLANT", "WHEAT"] for action in result.actions))
            self.assertGreater(result.pruned_illegal, 0)
        else:
            self.assertEqual(canonical, result.actions)

    def test_route_critical_inventory_transfer_is_canonical_only(self):
        state = fixture(1)
        # Candidate generation must not reinterpret destination-specific
        # logistics using only aggregate inventory economics.
        for action in (["PICKUP", "WHEAT", 1], ["DROP"], ["PLACE", "WHEAT", 1]):
            self.assertEqual((), tuple(bounded_worker_candidates(self.m, state, 0, action)))

    def test_candidate_family_is_bounded_and_deterministic(self):
        state = fixture(1)
        first = tuple(bounded_worker_candidates(self.m, state, 0, ["PASS"]))
        second = tuple(bounded_worker_candidates(self.m, copy.deepcopy(state), 0, ["PASS"]))
        self.assertEqual(first, second)
        self.assertIn(["PLANT", "WHEAT"], first)
        self.assertIn(["BUILD_COOP"], first)
        self.assertLessEqual(len(first), 16)

    def test_scorer_rewards_real_production_and_watered_survival(self):
        initial = fixture(1)
        planted = self.transition(initial, 0, ["PLANT", "WHEAT"])
        self.assertIsNotNone(planted)
        planted_score = score_components(self.m, planted, ScoreContext())
        watered = self.transition(planted, 0, ["WATER"])
        self.assertIsNotNone(watered)
        watered_score = score_components(self.m, watered, ScoreContext())
        self.assertGreater(planted_score["production"], 0)
        self.assertGreater(watered_score["survival"], planted_score["survival"])

    def test_proposer_preserves_controller_market_fields(self):
        canonical = {
            "farmer": ["PASS"],
            "hands": [["PASS"]],
            "market": [["SELL", "WHEAT", 1], ["BUY_PRODUCT", "CARROT", 1]],
            "hire": 1,
            "buyLand": 0,
        }
        proposed, result = propose_worker_action(
            canonical,
            fixture(2),
            lambda state, idx, base: bounded_worker_candidates(self.m, state, idx, base),
            self.transition,
            self.score,
            config=BeamConfig(width=24, depth=4, budget_ns=35_000_000),
        )
        self.assertEqual(canonical["market"], proposed["market"])
        self.assertEqual(canonical["hire"], proposed["hire"])
        self.assertEqual(canonical["buyLand"], proposed["buyLand"])
        if result.used_fallback:
            self.assertEqual(canonical, proposed)


if __name__ == "__main__":
    unittest.main()
