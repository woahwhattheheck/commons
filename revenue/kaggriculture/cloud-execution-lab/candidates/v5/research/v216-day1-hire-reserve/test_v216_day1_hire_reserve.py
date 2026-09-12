# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
from dataclasses import dataclass
import unittest

import v216_day1_hire_reserve as v216


@dataclass(frozen=True)
class Row:
    step: int
    payload: dict

    def action(self):
        return copy.deepcopy(self.payload)


@dataclass(frozen=True)
class Window:
    schema: str = v216.ROUTE_WITNESS_SCHEMA
    route_source: str = v216.ROUTE_WITNESS_SOURCE
    current_step: int = 23
    rows: tuple = ()


def window(hires=1, *, market_extra=()):
    market = [["HIRE"] for _ in range(hires)] + [list(x) for x in market_extra]
    return Window(rows=(Row(24, {"farmer": ["PASS"], "hands": [], "market": market}),))


def observation(*, money=0, wheat=3, price=20, farmer_pos=(1, 1), hand_pos=()):
    hands = [list(p) for p in hand_pos]
    positions = [list(farmer_pos), *hands]
    return {
        "step": 23,
        "player": 0,
        "farms": [
            {
                "farmer": positions[0],
                "hands": positions[1:],
                "money": money,
                "tiles": [[{} for _ in range(4)] for _ in range(4)],
            },
            {"farmer": [0, 0], "hands": [], "money": 0, "tiles": [[{}] * 4 for _ in range(4)]},
        ],
        "private": {
            "shed": {"WHEAT": wheat},
            "inventories": [{} for _ in positions],
        },
        "market": {"prices": {"WHEAT": price}},
    }


def action(*, farmer=("PASS",), hands=(), market=()):
    return {
        "farmer": list(farmer),
        "hands": [list(h) for h in hands],
        "market": [list(m) for m in market],
    }


class V216Tests(unittest.TestCase):
    def test_exact_one_hire_engages_and_sells_one(self):
        out, report = v216.transform_with_report(action(), observation(), window(1))
        self.assertEqual(out["market"], [["SELL", "WHEAT", 1]])
        self.assertTrue(report["engaged"])
        self.assertEqual(report["required_cash"], 1)

    def test_five_hires_use_fibonacci_prefix(self):
        out, report = v216.transform_with_report(action(), observation(money=0, price=12), window(5))
        self.assertEqual(report["required_cash"], 12)
        self.assertTrue(report["engaged"])
        self.assertEqual(out["market"], [["SELL", "WHEAT", 1]])

    def test_nonempty_selected_market_is_identity(self):
        base = action(market=(("SELL", "CARROT", 1),))
        out, report = v216.transform_with_report(base, observation(), window(1))
        self.assertEqual(out, base)
        self.assertEqual(report["reason"], "selected_market_nonempty")

    def test_only_step23_can_engage(self):
        obs = observation()
        obs["step"] = 22
        out, report = v216.transform_with_report(action(), obs, window(1))
        self.assertEqual(out["market"], [])
        self.assertEqual(report["reason"], "observation_or_step")

    def test_zero_or_six_hires_are_identity(self):
        for hires in (0, 6):
            with self.subTest(hires=hires):
                out, report = v216.transform_with_report(action(), observation(), window(hires))
                self.assertEqual(out["market"], [])
                self.assertEqual(report["reason"], "authored_hire_count")

    def test_cash_already_covers_committed_hires(self):
        out, report = v216.transform_with_report(action(), observation(money=4), window(4))
        self.assertEqual(report["required_cash"], 7)
        self.assertTrue(report["engaged"])
        out, report = v216.transform_with_report(action(), observation(money=7), window(4))
        self.assertEqual(out["market"], [])
        self.assertEqual(report["reason"], "cash_not_short")

    def test_single_wheat_sale_must_cover_entire_deficit(self):
        out, report = v216.transform_with_report(action(), observation(money=0, price=11), window(5))
        self.assertEqual(out["market"], [])
        self.assertEqual(report["reason"], "single_sale_cannot_fund")

    def test_preserves_two_projected_wheat(self):
        out, report = v216.transform_with_report(action(), observation(wheat=2), window(1))
        self.assertEqual(out["market"], [])
        self.assertEqual(report["reason"], "preserve_two_wheat")

    def test_pickup_projection_can_block(self):
        obs = observation(wheat=3)
        obs["private"]["inventories"] = [{}]
        base = action(farmer=("PICKUP", "WHEAT", 1))
        out, report = v216.transform_with_report(base, obs, window(1))
        self.assertEqual(out["market"], [])
        self.assertEqual(report["projected_wheat"], 2)

    def test_drop_projection_can_enable_and_respects_capacity_order(self):
        obs = observation(wheat=2)
        obs["private"]["inventories"] = [{"WHEAT": 1}]
        base = action(farmer=("DROP",))
        out, report = v216.transform_with_report(base, obs, window(1))
        self.assertTrue(report["engaged"])
        self.assertEqual(out["market"], [["SELL", "WHEAT", 1]])

        obs = observation(wheat=2)
        obs["private"]["shed"] = {"WHEAT": 2, "CARROT": 98}
        obs["private"]["inventories"] = [{"WHEAT": 1}]
        out, report = v216.transform_with_report(base, obs, window(1))
        self.assertFalse(report["engaged"])
        self.assertEqual(report["projected_wheat"], 2)

    def test_nonanimal_place_projection_can_enable(self):
        obs = observation(wheat=2)
        obs["private"]["inventories"] = [{"WHEAT": 1}]
        base = action(farmer=("PLACE", "WHEAT", 1))
        out, report = v216.transform_with_report(base, obs, window(1))
        self.assertTrue(report["engaged"])
        self.assertEqual(out["market"], [["SELL", "WHEAT", 1]])

    def test_animal_place_never_invents_wheat(self):
        obs = observation(wheat=2)
        obs["private"]["inventories"] = [{"WHEAT": 1, "SHEEP": 1}]
        base = action(farmer=("PLACE", "SHEEP", 1))
        out, report = v216.transform_with_report(base, obs, window(1))
        self.assertEqual(out["market"], [])
        self.assertEqual(report["projected_wheat"], 2)

    def test_multiplier_is_part_of_exact_cost_theorem(self):
        base = action()
        out, report = v216.transform_with_report(
            base, observation(money=1, price=5), window(3), {"farmHandCostMult": 2}
        )
        self.assertEqual(report["required_cash"], 8)
        self.assertEqual(report["deficit"], 7)
        self.assertEqual(out["market"], [])
        out, report = v216.transform_with_report(
            base, observation(money=1, price=7), window(3), {"farmHandCostMult": 2}
        )
        self.assertTrue(report["engaged"])

    def test_route_witness_must_be_landed_authority_and_exact_row24(self):
        for bad in (
            Window(schema="wrong", rows=window(1).rows),
            Window(route_source="wrong", rows=window(1).rows),
            Window(current_step=22, rows=window(1).rows),
            Window(rows=(Row(25, window(1).rows[0].payload),)),
            Window(rows=()),
        ):
            with self.subTest(bad=bad):
                out, report = v216.transform_with_report(action(), observation(), bad)
                self.assertEqual(out["market"], [])
                self.assertEqual(report["reason"], "route_witness")

    def test_worker_cardinality_and_malformed_shapes_fail_identity(self):
        obs = observation(hand_pos=((1, 1),))
        out, report = v216.transform_with_report(action(), obs, window(1))
        self.assertEqual(out["market"], [])
        self.assertEqual(report["reason"], "worker_cardinality")
        malformed = action()
        malformed["farmer"] = "PASS"
        out, report = v216.transform_with_report(malformed, observation(), window(1))
        self.assertEqual(out, malformed)
        self.assertEqual(report["reason"], "malformed_selected_action")

    def test_inputs_are_never_mutated(self):
        base = action()
        obs = observation()
        win = window(2)
        cfg = {"farmHandCostMult": 1}
        before = (copy.deepcopy(base), copy.deepcopy(obs), copy.deepcopy(win), copy.deepcopy(cfg))
        out = v216.transform(base, obs, win, cfg)
        self.assertEqual(out["market"], [["SELL", "WHEAT", 1]])
        self.assertEqual(base, before[0])
        self.assertEqual(obs, before[1])
        self.assertEqual(win, before[2])
        self.assertEqual(cfg, before[3])


if __name__ == "__main__":
    unittest.main()
