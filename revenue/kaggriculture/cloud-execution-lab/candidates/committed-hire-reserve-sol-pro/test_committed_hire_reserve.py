# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from committed_hire_reserve import (
    action_fingerprint,
    find_committed_hire,
    protect_committed_hire_seed_boundary,
)

HERE = Path(__file__).resolve().parent


def action(farmer=None, hands=None, market=None):
    return {"farmer": farmer or ["PASS"], "hands": hands or [], "market": market or []}


def route_fixture(*, trailing=True, plants=12):
    route = [action() for _ in range(64)]
    # Selection is step 1. Spread the exact MELON prefix over represented rows.
    for step in range(4, 4 + plants):
        route[step] = action(farmer=["PLANT", "MELON"])
    route[24] = action(market=[["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"]])
    for step in range(25, 48):
        final = ["EAST"] if trailing else ["PASS"]
        route[step] = action(
            farmer=["WEST"],
            hands=[["NORTH"], ["SOUTH"], ["WEST"], final],
        )
    route[48] = action(market=[["HIRE"]])
    return route


PREDECESSOR = action(
    farmer=["NORTH"],
    market=[
        ["SELL", "WHEAT", 8],
        ["BUY_SEED", "WHEAT", 7],
        ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"],
        ["BUY_ANIMAL", "COW", 2],
        ["BUY_ANIMAL", "SHEEP", 2],
    ],
)
CANDIDATE = action(
    farmer=["NORTH"],
    market=[
        ["SELL", "WHEAT", 9],
        ["BUY_SEED", "WHEAT", 7],
        ["BUY_SEED", "MELON", 12],
        ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"],
        ["BUY_ANIMAL", "COW", 2],
        ["BUY_ANIMAL", "SHEEP", 2],
    ],
)
CONFIG = {"maxMarketOrdersPerTurn": 10, "turnsPerDay": 24}


class GuardTests(unittest.TestCase):
    def test_exact_episode_shape_selects_predecessor(self):
        route = route_fixture()
        before_a, before_b, before_r = copy.deepcopy(PREDECESSOR), copy.deepcopy(CANDIDATE), copy.deepcopy(route)
        chosen, report = protect_committed_hire_seed_boundary(
            PREDECESSOR, CANDIDATE, route, 1, CONFIG, post_unit_seeds={"MELON": 0}
        )
        self.assertEqual(chosen, PREDECESSOR)
        self.assertTrue(report["certified"])
        self.assertEqual(report["crop"], "MELON")
        self.assertEqual(report["prefix_plant_requests"], 12)
        self.assertEqual(report["sell_quantity_delta"], 1)
        self.assertEqual(report["hire_witness"]["hire_step"], 24)
        self.assertEqual(report["hire_witness"]["hire_count"], 4)
        self.assertEqual(report["hire_witness"]["represented_rows"], 23)
        self.assertEqual((PREDECESSOR, CANDIDATE, route), (before_a, before_b, before_r))
        self.assertEqual(report["chosen_fingerprint"], action_fingerprint(PREDECESSOR))

    def test_no_trailing_actor_demand_is_unchanged(self):
        chosen, report = protect_committed_hire_seed_boundary(
            PREDECESSOR, CANDIDATE, route_fixture(trailing=False), 1, CONFIG,
            post_unit_seeds={"MELON": 0},
        )
        self.assertEqual(chosen, CANDIDATE)
        self.assertFalse(report["changed"])
        self.assertEqual(report["reason"], "no_contiguous_committed_hire")

    def test_route_switch_before_hire_is_unchanged(self):
        chosen, report = protect_committed_hire_seed_boundary(
            PREDECESSOR, CANDIDATE, route_fixture(), 1, CONFIG,
            post_unit_seeds={"MELON": 0}, route_switch_steps=[10],
        )
        self.assertEqual(chosen, CANDIDATE)
        self.assertEqual(report["reason"], "route_switch_crosses_workforce_window")

    def test_seed_delta_must_equal_complete_prefix(self):
        altered = copy.deepcopy(CANDIDATE)
        altered["market"][2][2] = 11
        chosen, report = protect_committed_hire_seed_boundary(
            PREDECESSOR, altered, route_fixture(), 1, CONFIG,
            post_unit_seeds={"MELON": 0},
        )
        self.assertEqual(chosen, altered)
        self.assertEqual(report["reason"], "seed_bundle_is_not_exact_zero_stock_prefix")

    def test_existing_seed_stock_is_unchanged(self):
        chosen, report = protect_committed_hire_seed_boundary(
            PREDECESSOR, CANDIDATE, route_fixture(), 1, CONFIG,
            post_unit_seeds={"MELON": 1},
        )
        self.assertEqual(chosen, CANDIDATE)
        self.assertFalse(report["certified"])

    def test_second_market_edit_is_unchanged(self):
        altered = copy.deepcopy(CANDIDATE)
        altered["market"][-1] = ["BUY_ANIMAL", "SHEEP", 1]
        chosen, report = protect_committed_hire_seed_boundary(
            PREDECESSOR, altered, route_fixture(), 1, CONFIG,
            post_unit_seeds={"MELON": 0},
        )
        self.assertEqual(chosen, altered)
        self.assertEqual(report["reason"], "candidate has an unsupported second market edit")

    def test_sell_delta_must_be_exactly_one(self):
        altered = copy.deepcopy(CANDIDATE)
        altered["market"][0][2] = 10
        chosen, report = protect_committed_hire_seed_boundary(
            PREDECESSOR, altered, route_fixture(), 1, CONFIG,
            post_unit_seeds={"MELON": 0},
        )
        self.assertEqual(chosen, altered)
        self.assertEqual(report["reason"], "SELL edit must add exactly one unit")

    def test_unit_change_is_unchanged(self):
        altered = copy.deepcopy(CANDIDATE)
        altered["farmer"] = ["SOUTH"]
        chosen, report = protect_committed_hire_seed_boundary(
            PREDECESSOR, altered, route_fixture(), 1, CONFIG,
            post_unit_seeds={"MELON": 0},
        )
        self.assertEqual(chosen, altered)
        self.assertEqual(report["reason"], "unit actions differ")

    def test_malformed_workforce_row_is_unchanged(self):
        route = route_fixture()
        route[30]["hands"] = "not-a-list"
        chosen, report = protect_committed_hire_seed_boundary(
            PREDECESSOR, CANDIDATE, route, 1, CONFIG,
            post_unit_seeds={"MELON": 0},
        )
        self.assertEqual(chosen, CANDIDATE)
        self.assertEqual(report["reason"], "workforce_cardinality_is_not_contiguous")

    def test_unsupported_market_operation_is_unchanged(self):
        altered = copy.deepcopy(CANDIDATE)
        altered["market"][2] = ["BORROW", "MELON", 12]
        chosen, report = protect_committed_hire_seed_boundary(
            PREDECESSOR, altered, route_fixture(), 1, CONFIG,
            post_unit_seeds={"MELON": 0},
        )
        self.assertEqual(chosen, altered)
        self.assertEqual(report["reason"], "unsupported market operation BORROW")

    def test_outside_opening_step_is_unchanged(self):
        chosen, report = protect_committed_hire_seed_boundary(
            PREDECESSOR, CANDIDATE, route_fixture(), 2, CONFIG,
            post_unit_seeds={"MELON": 0},
        )
        self.assertEqual(chosen, CANDIDATE)
        self.assertEqual(report["reason"], "outside_witnessed_opening_step")

    def test_hire_arithmetic_witness(self):
        evidence = json.loads((HERE / "evidence" / "episode-107130860-causal-witness.json").read_text())
        costs = evidence["hire_boundary"]["costs"]
        self.assertEqual(sum(costs), 7)
        self.assertEqual(evidence["hire_boundary"]["v2_cash_before"], 6)
        self.assertEqual(sum(costs[:3]), 4)
        self.assertGreater(sum(costs), evidence["hire_boundary"]["v2_cash_before"])
        self.assertEqual(evidence["hire_boundary"]["v2_completed"], 3)
        self.assertEqual(evidence["hire_boundary"]["v1_completed"], 4)
        self.assertEqual(evidence["downstream"]["unreachable_fourth_hand_rows"], 23)

    def test_witness_function_is_deterministic(self):
        route = route_fixture()
        self.assertEqual(find_committed_hire(route, 1, CONFIG), find_committed_hire(route, 1, CONFIG))


if __name__ == "__main__":
    unittest.main(verbosity=2)
