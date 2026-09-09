# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from official_shadow_oracle import (
    active_market_prefix,
    audit_contracts,
    legal_buy_product,
    minimize_atomic_plant,
    normalize_action,
    official_atomic_plant,
    official_joint_sell,
    sequential_joint_sell_shadow,
    sequential_plant_shadow,
    shed_deposit_fits,
    state_activated,
)


class OfficialShadowOracleTests(unittest.TestCase):
    def test_atomic_plant_blocks_every_same_crop_request(self):
        actual = official_atomic_plant(
            [["PLANT", "WHEAT"], ["PLANT", "WHEAT"]],
            {"WHEAT": 1},
        )
        self.assertEqual(("WHEAT",), actual.blocked_crops)
        self.assertEqual((["PASS"], ["PASS"]), actual.executable)
        self.assertEqual((("WHEAT", 1),), actual.remaining_seeds)

    def test_atomic_plant_only_blocks_oversubscribed_crop(self):
        actual = official_atomic_plant(
            [["PLANT", "WHEAT"], ["PLANT", "WHEAT"], ["PLANT", "CARROT"]],
            {"WHEAT": 1, "CARROT": 1},
        )
        self.assertEqual(("WHEAT",), actual.blocked_crops)
        self.assertEqual((["PASS"], ["PASS"], ["PLANT", "CARROT"]), actual.executable)
        self.assertEqual((("CARROT", 0), ("WHEAT", 1)), actual.remaining_seeds)

    def test_minimizer_shrinks_live_sequential_defect(self):
        counterexample = minimize_atomic_plant(
            [["PASS"], ["PLANT", "WHEAT"], ["PLANT", "WHEAT"], ["PASS"]],
            {"WHEAT": 1, "CARROT": 9},
            sequential_plant_shadow,
        )
        self.assertIsNotNone(counterexample)
        assert counterexample is not None
        self.assertEqual(
            [["PLANT", "WHEAT"], ["PLANT", "WHEAT"]],
            counterexample.fixture["actions"],
        )
        self.assertEqual({"WHEAT": 1}, counterexample.fixture["seeds"])
        self.assertEqual(64, len(counterexample.fingerprint))

    def test_market_is_truncated_before_order_parsing(self):
        action = {"market": [["BAD"], ["SELL", "WHEAT", 1], ["SELL", "WHEAT", 99]]}
        self.assertEqual([["BAD"], ["SELL", "WHEAT", 1]], active_market_prefix(action, 2))

    def test_normalization_treats_non_list_hands_and_market_as_empty(self):
        normalized = normalize_action({"hands": "not-a-list", "market": None}, 2, 4)
        self.assertEqual([["PASS"], ["PASS"]], normalized["hands"])
        self.assertEqual([], normalized["market"])

    def test_buy_product_domain_is_not_all_products(self):
        self.assertTrue(legal_buy_product("WHEAT"))
        self.assertTrue(legal_buy_product("FERTILIZER"))
        for illegal in ("CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL"):
            self.assertFalse(legal_buy_product(illegal))

    def test_exact_capacity_boundary_is_legal(self):
        self.assertTrue(shed_deposit_fits(99, 1, 100))
        self.assertTrue(shed_deposit_fits(100, 0, 100))
        self.assertFalse(shed_deposit_fits(100, 1, 100))

    def test_activation_requires_post_state_change(self):
        before = {"money": 500, "shed": {}}
        self.assertFalse(state_activated(before, copy.deepcopy(before)))
        self.assertTrue(state_activated(before, {"money": 501, "shed": {}}))

    def test_joint_market_quotes_both_players_before_commit(self):
        quote = lambda inventory: 30 - inventory
        official = official_joint_sell(10, (1, 1), (1, 1), quote)
        sequential = sequential_joint_sell_shadow(10, (1, 1), (1, 1), quote)
        self.assertEqual(((20,), (20,)), official.quotes)
        self.assertEqual(((20,), (19,)), sequential.quotes)
        self.assertNotEqual(official, sequential)

    def test_audit_is_deterministic_and_all_sentries_fire(self):
        first = audit_contracts()
        second = audit_contracts()
        self.assertEqual(first, second)
        self.assertTrue(all(first["rules"].values()))
        self.assertEqual(2, len(first["counterexamples"]))
        self.assertEqual(64, len(first["evidence_hash"]))

    def test_audit_matches_committed_golden_receipt(self):
        fixture = Path(__file__).resolve().parent / "fixtures" / "expected-evidence.json"
        expected = json.loads(fixture.read_text(encoding="utf-8"))
        actual = json.loads(json.dumps(audit_contracts(), sort_keys=True))
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
