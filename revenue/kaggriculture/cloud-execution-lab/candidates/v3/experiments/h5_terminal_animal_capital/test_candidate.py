# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("h5_candidate", HERE / "candidate.py")
h5 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(h5)


def obs(step):
    return {"step": step}


def action(market=None):
    return {
        "farmer": ["DROP"],
        "hands": [["HARVEST"], ["WEST"]],
        "market": deepcopy(market or []),
    }


class H5TerminalAnimalCapitalTests(unittest.TestCase):
    def test_disabled_is_exact_object_identity(self):
        original = action([["BUY_ANIMAL", "COW", 2]])
        out, report = h5.apply_terminal_animal_capital_guard(
            obs(700), original, enabled=False
        )
        self.assertIs(out, original)
        self.assertEqual("OFF", report["reason"])

    def test_before_final_plan_is_exact_identity(self):
        original = action([["BUY_ANIMAL", "GOOSE", 1]])
        out, report = h5.apply_terminal_animal_capital_guard(
            obs(647), original, enabled=True
        )
        self.assertIs(out, original)
        self.assertEqual("BEFORE_FINAL_PLAN", report["reason"])

    def test_step648_all_standard_animals_are_dead_capital(self):
        original = action([
            ["SELL", "WOOL", 2],
            ["BUY_ANIMAL", "GOOSE", 1],
            ["BUY_ANIMAL", "SHEEP", 2],
            ["BUY_ANIMAL", "COW", 3],
        ])
        out, report = h5.apply_terminal_animal_capital_guard(
            obs(648), original, enabled=True
        )
        self.assertEqual(
            [["SELL", "WOOL", 2], [], [], []], out["market"]
        )
        self.assertEqual([1, 2, 3], report["dropped_indices"])
        self.assertEqual(
            {"GOOSE": 1, "SHEEP": 2, "COW": 3}, report["dropped_units"]
        )
        self.assertEqual(original["farmer"], out["farmer"])
        self.assertEqual(original["hands"], out["hands"])

    def test_terminal_liquidation_without_animal_buy_is_identity(self):
        original = action([
            ["SELL", "MILK", 5],
            ["SELL", "STRAWBERRY", 7],
        ])
        out, report = h5.apply_terminal_animal_capital_guard(
            obs(718), original, enabled=True
        )
        self.assertIs(out, original)
        self.assertEqual("NO_PROVABLY_DEAD_ANIMAL_CAPITAL", report["reason"])

    def test_sell_and_placeholders_may_follow_safe_dead_buy(self):
        original = action([
            ["BUY_ANIMAL", "COW", 1],
            [],
            ["SELL", "WOOL", 4],
        ])
        out, report = h5.apply_terminal_animal_capital_guard(
            obs(700), original, enabled=True
        )
        self.assertEqual([[], [], ["SELL", "WOOL", 4]], out["market"])
        self.assertEqual([0], report["dropped_indices"])

    def test_later_cash_spend_protects_earlier_dead_buy(self):
        original = action([
            ["BUY_ANIMAL", "COW", 1],
            ["BUY_PRODUCT", "WHEAT", 2],
        ])
        out, report = h5.apply_terminal_animal_capital_guard(
            obs(700), original, enabled=True
        )
        self.assertIs(out, original)
        self.assertEqual("DOWNSTREAM_AFFORDABILITY_AMBIGUITY", report["reason"])

    def test_only_safe_dead_suffix_is_dropped(self):
        original = action([
            ["BUY_ANIMAL", "COW", 1],
            ["HIRE"],
            ["BUY_ANIMAL", "SHEEP", 2],
            ["SELL", "WOOL", 4],
        ])
        out, report = h5.apply_terminal_animal_capital_guard(
            obs(700), original, enabled=True
        )
        self.assertEqual([
            ["BUY_ANIMAL", "COW", 1],
            ["HIRE"],
            [],
            ["SELL", "WOOL", 4],
        ], out["market"])
        self.assertEqual([2], report["dropped_indices"])
        self.assertEqual(1, report["protected_prefix_through"])

    def test_unknown_later_order_is_protected(self):
        original = action([
            ["BUY_ANIMAL", "GOOSE", 1],
            ["FUTURE_SPEND", 10],
        ])
        out, report = h5.apply_terminal_animal_capital_guard(
            obs(700), original, enabled=True
        )
        self.assertIs(out, original)
        self.assertEqual("DOWNSTREAM_AFFORDABILITY_AMBIGUITY", report["reason"])

    def test_nonstandard_timing_config_is_identity(self):
        original = action([["BUY_ANIMAL", "GOOSE", 1]])
        for cfg in (
            {"turnsPerDay": 23},
            {"episodeSteps": 900},
            {"turnsPerDay": 24.0},
            {"turnsPerDay": True},
            {"turnsPerDay": "24"},
            {"episodeSteps": 720.0},
            {"episodeSteps": True},
            {"episodeSteps": "720"},
        ):
            with self.subTest(cfg=cfg):
                out, report = h5.apply_terminal_animal_capital_guard(
                    obs(700), original, cfg, enabled=True
                )
                self.assertIs(out, original)
                self.assertEqual("NONSTANDARD_CONFIG", report["reason"])

    def test_malformed_step_types_are_identity(self):
        original = action([["BUY_ANIMAL", "GOOSE", 1]])
        for step in (True, 700.0, "700", None):
            with self.subTest(step=step):
                out, report = h5.apply_terminal_animal_capital_guard(
                    obs(step), original, enabled=True
                )
                self.assertIs(out, original)
                self.assertEqual("BAD_STEP", report["reason"])

    def test_after_last_action_is_identity(self):
        original = action([["BUY_ANIMAL", "COW", 1]])
        out, report = h5.apply_terminal_animal_capital_guard(
            obs(719), original, enabled=True
        )
        self.assertIs(out, original)
        self.assertEqual("AFTER_LAST_ACTION", report["reason"])

    def test_malformed_known_animal_quantities_fail_closed(self):
        for quantity in (True, 1.0, "1", 0, -1):
            original = action([["BUY_ANIMAL", "COW", quantity]])
            with self.subTest(quantity=quantity):
                out, report = h5.apply_terminal_animal_capital_guard(
                    obs(700), original, enabled=True
                )
                self.assertIs(out, original)
                self.assertEqual("BAD_BUY_ANIMAL_ROW", report["reason"])

    def test_malformed_market_row_fails_closed(self):
        original = action([["BUY_ANIMAL", "COW", 1], ("SELL", "WOOL", 2)])
        out, report = h5.apply_terminal_animal_capital_guard(
            obs(700), original, enabled=True
        )
        self.assertIs(out, original)
        self.assertEqual("BAD_MARKET_ROW", report["reason"])

    def test_unknown_animal_is_never_optimized(self):
        original = action([["BUY_ANIMAL", "ALPACA", 1]])
        out, report = h5.apply_terminal_animal_capital_guard(
            obs(700), original, enabled=True
        )
        self.assertIs(out, original)
        self.assertEqual("NO_PROVABLY_DEAD_ANIMAL_CAPITAL", report["reason"])

    def test_wrapper_preserves_parent_when_disabled(self):
        original = action([["BUY_ANIMAL", "COW", 1]])

        def parent(observation, configuration=None):
            return original

        wrapped = h5.wrap_agent(parent, enabled=False)
        self.assertIs(wrapped(obs(700), {"episodeSteps": 720}), original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
