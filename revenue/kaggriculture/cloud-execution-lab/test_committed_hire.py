# SPDX-License-Identifier: Apache-2.0
"""Contracts for the additive committed-HIRE solvency candidate."""
from __future__ import annotations

from copy import deepcopy
import unittest

import committed_hire as ch
import frozen_selected as fs


def action(*, hands=None, market=None):
    return {
        "farmer": ["PASS"],
        "hands": deepcopy(hands or []),
        "market": deepcopy(market or []),
    }


def fixture():
    config = {
        "shedCapacity": 100,
        "farmHandCostMult": 1,
        "maxMarketOrdersPerTurn": 10,
        "turnsPerDay": 24,
        "episodeSteps": 720,
        "committedHireUseLookahead": 8,
    }
    farm = {
        "money": 6,
        "farmer": [4, 4],
        "hands": [],
        "unlocked_quadrants": ["NW"],
        "hires_today": 0,
        "tiles": [[None for _ in range(10)] for _ in range(10)],
    }
    shed = {item: 0 for item in fs.m.PRODUCTS + list(fs.m.ANIMALS)}
    shed["MILK"] = 1
    private = {
        "shed": shed,
        "seeds": {item: 0 for item in fs.m.CROPS},
        "inventories": [{}],
    }
    inventory = {item: 10000 for item in fs.m.PRODUCTS}
    obs = {
        "step": 24,
        "player": 0,
        "farms": [deepcopy(farm), deepcopy(farm)],
        "private": deepcopy(private),
        "market": {
            "inventory": inventory,
            "prices": {item: fs.m.market_price(item, inventory[item]) for item in inventory},
            "params": None,
        },
        "town": {"unlocked_shops": []},
    }
    route = [action() for _ in range(40)]
    route[25] = action(market=[["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"]])
    route[26] = action(
        hands=[["NORTH"], ["SOUTH"], ["EAST"], ["WEST"]]
    )
    return config, farm, private, obs, route


class CommitmentProofTests(unittest.TestCase):
    def test_fourth_slot_use_closes_over_all_four_hires(self):
        config, farm, _private, _obs, route = fixture()
        report = ch.committed_next_hires(route, 24, farm, [], config)
        self.assertEqual(report["status"], "committed")
        self.assertEqual(report["committed_hire_indices"], (0, 1, 2, 3))
        self.assertEqual(report["required_hires"], 4)

    def test_pass_only_new_slot_is_not_a_commitment(self):
        config, farm, _private, _obs, route = fixture()
        route[26]["hands"][3] = ["PASS"]
        report = ch.committed_next_hires(route, 24, farm, [], config)
        self.assertEqual(report["required_hires"], 3)
        self.assertEqual(report["committed_hire_indices"], (0, 1, 2))

    def test_decision_checkpoint_is_a_hard_boundary(self):
        config, farm, _private, _obs, route = fixture()
        report = ch.committed_next_hires(route, 24, farm, [], config, ((26, "x", 1, "tail"),))
        self.assertEqual(report["status"], "inactive")
        self.assertEqual(report["reason"], "new-hand-slots-unused")
        self.assertEqual(report["decision_barrier"], 26)

    def test_current_hire_fails_closed(self):
        config, farm, _private, _obs, route = fixture()
        report = ch.committed_next_hires(route, 24, farm, [["HIRE"]], config)
        self.assertEqual(report["status"], "inactive")
        self.assertEqual(report["reason"], "current-hire-outside-one-turn-proof")

    def test_pinned_main_route_contains_the_documented_step_25_commitment(self):
        config, farm, _private, _obs, _route = fixture()
        route = fs.parent.routes()[fs.parent.MAIN]
        report = ch.committed_next_hires(
            route, 24, farm, [], config, fs.parent.DECISIONS
        )
        self.assertEqual(report["required_hires"], 4)
        self.assertEqual(report["committed_hire_indices"], (0, 1, 2, 3))
        # This line is intentionally visible in Actions logs for source review.
        print("PINNED_ROUTE_24_MARKET", route[24].get("market", []))
        print("PINNED_ROUTE_25_MARKET", route[25].get("market", []))
        print("PINNED_ROUTE_COMMITMENT", report)


class ReserveTests(unittest.TestCase):
    def test_price_floor_one_sale_closes_exact_six_to_seven_gap(self):
        config, farm, private, obs, route = fixture()
        report = ch.committed_hire_reserve(
            fs,
            obs,
            config,
            {"market": []},
            farm,
            private,
            route,
            {"MILK": 0},
            {"MILK": 1},
        )
        self.assertEqual(report["status"], "certified")
        self.assertEqual(report["owner_item"], "MILK")
        self.assertEqual(report["minimum_now"], 1)
        self.assertEqual(report["required_cash"], 7)
        self.assertEqual(report["baseline"]["cash_floor"], 6)
        self.assertEqual(report["candidate"]["cash_floor"], 7)
        self.assertEqual(report["requested_receipt_credit"], 0)
        self.assertEqual(report["cost"]["future_sale_credit"], 0)

    def test_baseline_seven_dollars_is_unchanged(self):
        config, farm, private, obs, route = fixture()
        farm["money"] = 7
        report = ch.committed_hire_reserve(
            fs, obs, config, {"market": []}, farm, private, route,
            {"MILK": 0}, {"MILK": 1},
        )
        self.assertEqual(report["status"], "already-funded")
        self.assertIsNone(report["owner_item"])

    def test_intervening_current_purchase_fails_closed(self):
        config, farm, private, obs, route = fixture()
        report = ch.committed_hire_reserve(
            fs, obs, config, {"market": [["BUY_SEED", "CARROT", 1]]},
            farm, private, route, {"MILK": 0}, {"MILK": 1},
        )
        self.assertEqual(report["status"], "inactive")
        self.assertEqual(report["reason"], "current-prefix-not-sell-only")

    def test_intervening_next_purchase_fails_closed(self):
        config, farm, private, obs, route = fixture()
        route[25]["market"].insert(0, ["BUY_SEED", "CARROT", 1])
        report = ch.committed_hire_reserve(
            fs, obs, config, {"market": []}, farm, private, route,
            {"MILK": 0}, {"MILK": 1},
        )
        self.assertEqual(report["status"], "inactive")
        self.assertEqual(report["reason"], "next-prefix-not-sell-hire-only")

    def test_operating_stock_is_never_new_liquidation(self):
        config, farm, private, obs, route = fixture()
        private["shed"]["MILK"] = 0
        private["shed"]["WHEAT"] = 10
        report = ch.committed_hire_reserve(
            fs, obs, config, {"market": []}, farm, private, route,
            {"WHEAT": 0}, {"WHEAT": 10},
        )
        self.assertEqual(report["status"], "inactive")
        self.assertEqual(report["reason"], "no-safe-non-operating-sale")

    def test_full_market_without_matching_sale_slot_fails_closed(self):
        config, farm, private, obs, route = fixture()
        full = [["SELL", "WHEAT", 0] for _ in range(10)]
        report = ch.committed_hire_reserve(
            fs, obs, config, {"market": full}, farm, private, route,
            {"MILK": 0}, {"MILK": 1},
        )
        self.assertEqual(report["status"], "inactive")
        self.assertEqual(report["reason"], "no-safe-non-operating-sale")


class FundingIntegrationTests(unittest.TestCase):
    def tearDown(self):
        ch.uninstall(fs)

    def test_legacy_trace_preserves_three_but_patch_commits_fourth(self):
        config, farm, private, obs, route = fixture()
        base = {"market": []}
        current = {"MILK": 0}
        targets = {"MILK": 1}

        ch.uninstall(fs)
        legacy, legacy_certificate = fs.funded_minimum_now(
            obs, config, base, farm, private, route, 32,
            current, targets, "MILK",
        )
        self.assertEqual(legacy, 0)
        self.assertEqual(legacy_certificate["reference_acquisitions"], 3)

        ch.install(fs)
        minimum, certificate = fs.funded_minimum_now(
            obs, config, base, farm, private, route, 32,
            current, targets, "MILK",
        )
        self.assertEqual(minimum, 1)
        self.assertTrue(certificate["committed_hire_applied"])
        self.assertEqual(
            certificate["committed_hire_reserve"]["commitment"]["required_hires"], 4
        )

    def test_install_is_idempotent(self):
        ch.uninstall(fs)
        original = fs.funded_minimum_now
        ch.install(fs)
        patched = fs.funded_minimum_now
        ch.install(fs)
        self.assertIs(fs.funded_minimum_now, patched)
        self.assertIsNot(patched, original)

    def test_unrelated_clipped_purchase_retains_legacy_behavior(self):
        config, farm, private, obs, route = fixture()
        obs["step"] = 5
        farm["money"] = 0
        route = [action() for _ in range(20)]
        route[6] = action(market=[["BUY_ANIMAL", "COW", 1]])
        private["shed"]["MILK"] = 10
        base = {"market": [["BUY_ANIMAL", "COW", 1], ["SELL", "MILK", 10]]}
        current = {"MILK": 10}
        targets = {"MILK": 10}

        ch.install(fs)
        minimum, certificate = fs.funded_minimum_now(
            obs, config, base, farm, private, route, 6,
            current, targets, "MILK",
        )
        self.assertEqual(minimum, 0)
        self.assertFalse(certificate["committed_hire_applied"])


class ActorArityTests(unittest.TestCase):
    def test_surplus_is_trimmed_and_missing_rows_are_pass(self):
        observation = {
            "player": 0,
            "farms": [{"hands": [[1, 1], [2, 2]]}],
        }
        source = {
            "farmer": ["PASS"],
            "hands": [["NORTH"], ["SOUTH"], ["EAST"]],
            "market": [],
        }
        trimmed = ch.normalize_actor_arity(source, observation)
        self.assertEqual(trimmed["hands"], [["NORTH"], ["SOUTH"]])
        self.assertEqual(len(source["hands"]), 3)

        source["hands"] = [["NORTH"]]
        padded = ch.normalize_actor_arity(source, observation)
        self.assertEqual(padded["hands"], [["NORTH"], ["PASS"]])


if __name__ == "__main__":
    unittest.main()
