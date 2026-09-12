# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

from certified_route_runtime import (
    CertifiedLeaderRoutePolicy,
    canonical,
    prestate_certificate,
)


def configuration(**updates):
    value = {
        "boardSize": 10,
        "turnsPerDay": 24,
        "shedCapacity": 100,
        "maxMarketOrdersPerTurn": 10,
        "farmHandCostMult": 1,
        "marketParams": {"WHEAT": {"basePrice": 10}},
    }
    value.update(updates)
    return value


def farm(money=100, hands=None):
    return {
        "money": money,
        "hands": [] if hands is None else hands,
        "hires_today": 0,
        "unlocked_quadrants": ["NW"],
        "tiles": [{"location": [0, 0], "entity": None}],
        "farmer": {"location": [0, 0], "inventory": []},
    }


def observation(step=24, player=0, money=100, rival_money=77, hands=None):
    return {
        "step": step,
        "day": 1,
        "player": player,
        "farms": [farm(money, hands), farm(rival_money)],
        "private": {"shed": {"WHEAT": 2}, "seeds": {"WHEAT": 1}},
        "market": {"inventory": {"WHEAT": 10000}, "shops": []},
    }


def route_action():
    return {
        "farmer": ["MOVE", "EAST"],
        "hands": [],
        "market": [["SELL", "WHEAT", 1]],
    }


def baseline_action():
    return {"farmer": ["PASS"], "hands": [], "market": []}


class Baseline:
    def __init__(self):
        self.calls = []

    def __call__(self, obs, cfg=None):
        self.calls.append(obs["step"])
        return baseline_action()


class MutatingBaseline(Baseline):
    def __call__(self, obs, cfg=None):
        self.calls.append(obs["step"])
        obs["farms"][0]["money"] = -999
        if cfg is not None:
            cfg["boardSize"] = 999
        return baseline_action()


class CertifiedRuntimeTests(unittest.TestCase):
    def row(self, obs, cfg, action=None):
        action = action or route_action()
        return {
            "action": action,
            "certificate": prestate_certificate(obs, cfg, action, seat=0, mode="full"),
        }

    def test_matching_row_emits_route_after_advancing_incumbent(self):
        obs, cfg = observation(), configuration()
        base = Baseline()
        policy = CertifiedLeaderRoutePolicy(
            base,
            {"24": self.row(obs, cfg)},
            mode="post24_full",
            source_seat=0,
        )
        self.assertEqual(policy.agent(obs, cfg), route_action())
        self.assertEqual(base.calls, [24])
        self.assertEqual(policy.diagnostics()["certificate_matches"], 1)

    def test_state_mismatch_hands_off_before_route_emission_and_is_permanent(self):
        source, cfg = observation(), configuration()
        row24 = self.row(source, cfg)
        source25 = observation(step=25)
        row25 = self.row(source25, cfg)
        base = Baseline()
        policy = CertifiedLeaderRoutePolicy(
            base,
            {"24": row24, "25": row25},
            mode="post24_full",
            source_seat=0,
        )
        live24 = observation(money=101)
        self.assertEqual(policy.agent(live24, cfg), baseline_action())
        self.assertEqual(policy.agent(source25, cfg), baseline_action())
        self.assertEqual(base.calls, [24, 25])
        diagnostics = policy.diagnostics()
        self.assertFalse(diagnostics["active"])
        self.assertEqual(diagnostics["handoff_step"], 24)
        self.assertEqual(diagnostics["activation_count"], 0)

    def test_source_seat_mismatch_is_exact_fallback(self):
        source, cfg = observation(), configuration()
        live = observation(player=1)
        base = Baseline()
        policy = CertifiedLeaderRoutePolicy(
            base,
            {"24": self.row(source, cfg)},
            mode="post24_full",
            source_seat=0,
        )
        self.assertEqual(policy.agent(live, cfg), baseline_action())
        self.assertEqual(policy.diagnostics()["handoff_reason"], "source_seat_mismatch")
        self.assertEqual(policy.diagnostics()["certificate_checks"], 0)

    def test_configuration_drift_fails_closed(self):
        obs, cfg = observation(), configuration()
        base = Baseline()
        policy = CertifiedLeaderRoutePolicy(
            base,
            {"24": self.row(obs, cfg)},
            mode="post24_full",
            source_seat=0,
        )
        self.assertEqual(
            policy.agent(obs, configuration(maxMarketOrdersPerTurn=1)),
            baseline_action(),
        )
        self.assertFalse(policy.diagnostics()["active"])

    def test_missing_or_malformed_row_fails_closed(self):
        obs, cfg = observation(), configuration()
        for tape in ({}, {"24": {"action": route_action(), "certificate": {"mode": "full"}}}):
            with self.subTest(tape=tape):
                base = Baseline()
                policy = CertifiedLeaderRoutePolicy(
                    base,
                    tape,
                    mode="post24_full",
                    source_seat=0,
                )
                self.assertEqual(policy.agent(obs, cfg), baseline_action())
                self.assertFalse(policy.diagnostics()["active"])

    def test_inputs_are_not_mutated(self):
        obs, cfg = observation(), configuration()
        action = route_action()
        row = self.row(obs, cfg, action)
        originals = copy.deepcopy((obs, cfg, action, row))
        policy = CertifiedLeaderRoutePolicy(
            Baseline(),
            {"24": row},
            mode="post24_full",
            source_seat=0,
        )
        policy.agent(obs, cfg)
        self.assertEqual((obs, cfg, action, row), originals)

    def test_mutating_incumbent_cannot_corrupt_certified_prestate_or_inputs(self):
        obs, cfg = observation(), configuration()
        original_obs, original_cfg = copy.deepcopy(obs), copy.deepcopy(cfg)
        base = MutatingBaseline()
        policy = CertifiedLeaderRoutePolicy(
            base,
            {"24": self.row(obs, cfg)},
            mode="post24_full",
            source_seat=0,
        )
        self.assertEqual(policy.agent(obs, cfg), route_action())
        self.assertEqual(obs, original_obs)
        self.assertEqual(cfg, original_cfg)
        self.assertEqual(base.calls, [24])
        self.assertEqual(policy.diagnostics()["certificate_matches"], 1)

    def test_rival_farm_and_step_are_outside_reviewed_certificate_domain(self):
        cfg, action = configuration(), route_action()
        left = observation(step=24, rival_money=1)
        right = observation(step=25, rival_money=999999)
        self.assertEqual(
            canonical(prestate_certificate(left, cfg, action, seat=0, mode="full")),
            canonical(prestate_certificate(right, cfg, action, seat=0, mode="full")),
        )

    def test_step_zero_resets_latched_handoff(self):
        source, cfg = observation(), configuration()
        base = Baseline()
        policy = CertifiedLeaderRoutePolicy(
            base,
            {"24": self.row(source, cfg)},
            mode="post24_full",
            source_seat=0,
        )
        policy.agent(observation(money=101), cfg)
        self.assertFalse(policy.diagnostics()["active"])
        policy.agent(observation(step=0), cfg)
        self.assertTrue(policy.diagnostics()["active"])
        self.assertIsNone(policy.diagnostics()["handoff_step"])

    def test_market_limit_is_applied_only_after_certificate_match(self):
        obs, cfg = observation(), configuration(maxMarketOrdersPerTurn=1)
        action = route_action()
        action["market"].append(["BUY_PRODUCT", "FERTILIZER", 1])
        row = self.row(obs, cfg, action)
        policy = CertifiedLeaderRoutePolicy(
            Baseline(),
            {"24": row},
            mode="post24_full",
            source_seat=0,
        )
        emitted = policy.agent(obs, cfg)
        self.assertEqual(emitted["market"], [["SELL", "WHEAT", 1]])
        self.assertEqual(policy.diagnostics()["certificate_matches"], 1)


if __name__ == "__main__":
    unittest.main()
