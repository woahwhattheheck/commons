# SPDX-License-Identifier: Apache-2.0
"""Predecessor-discriminating contracts for receding reserve release."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for path in (str(HERE), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from bootstrap import install_source_paths

install_source_paths()

import frozen_selected
import reserve_release as rr
import scheduler as s
import test_engine_semantics as semantics
from test_scheduler import FixedController


PASS = {"farmer": ["PASS"], "hands": [], "market": []}


class RecedingReserveReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        semantics.EngineSemantics.setUpClass()
        cls.helper = semantics.EngineSemantics()

    def setUp(self):
        rr.restore()

    def tearDown(self):
        rr.restore()

    def fixture(self, *, step=20, milk=10, wheat=90, cash=10000):
        state, env = self.helper.fixture(
            stock=(milk, 0), step=step, cash=cash
        )
        obs = state[0].observation
        obs.private["shed"]["WHEAT"] = wheat
        return state, env, obs

    def scheduler(self, now, base, future=None):
        owner = s.SellScheduler()
        owner.controller = FixedController(now, base, future)
        owner.joint_producer_busy = False
        return owner

    def profiles(self, owner, obs, base, cfg, *, end, item="MILK"):
        farm, private = s.post_units(obs, base, cfg)
        predecessor = rr.predecessor_receipt_profile()(
            owner, obs, base, farm, private, end, item, cfg
        )
        rr.install()
        candidate = owner.receipt_profile(
            obs, base, farm, private, end, item, cfg
        )
        return predecessor, candidate

    def test_exact_full_safe_carry_is_the_only_new_admission(self):
        _, env, obs = self.fixture()
        owner = self.scheduler(20, PASS, {21: PASS})
        predecessor, candidate = self.profiles(
            owner, obs, PASS, env.configuration, end=21
        )
        self.assertFalse(predecessor(()))
        self.assertTrue(candidate(()))
        certificate = rr.reserve_release_certificate(
            owner, obs, PASS, env.configuration
        )
        self.assertEqual(
            certificate,
            {
                "eligible": True,
                "reason": "next_pre_market_growth_zero",
                "next_step": 21,
                "capacity": 100,
                "current_requested_total": 100,
            },
        )

    def test_official_engine_allows_exact_full_but_blocks_the_next_buy(self):
        state, env, _ = self.fixture(milk=10, wheat=89, cash=100000)
        self.helper.market(
            state, env, [["BUY_PRODUCT", "WHEAT", 1]]
        )
        private = state[0].observation.private
        first_cash = state[0].observation.farms[0]["money"]
        self.assertEqual(sum(private["shed"].values()), 100)
        self.assertEqual(private["shed"]["WHEAT"], 90)

        self.helper.market(
            state, env, [["BUY_PRODUCT", "WHEAT", 1]]
        )
        self.assertEqual(sum(private["shed"].values()), 100)
        self.assertEqual(private["shed"]["WHEAT"], 90)
        self.assertEqual(state[0].observation.farms[0]["money"], first_cash)

    def test_current_unit_overflow_cannot_be_rescued_by_market(self):
        _, env, obs = self.fixture(milk=10, wheat=89)
        obs.private["inventories"] = [{"MILK": 2}]
        base = {"farmer": ["DROP"], "hands": [], "market": []}
        owner = self.scheduler(20, base, {21: PASS})
        predecessor, candidate = self.profiles(
            owner, obs, base, env.configuration, end=21
        )
        plan = ((20, 1),)
        self.assertFalse(predecessor(plan))
        self.assertFalse(candidate(plan))
        certificate = rr.reserve_release_certificate(
            owner, obs, base, env.configuration
        )
        self.assertEqual(certificate["reason"], "current_unit_overflow")
        self.assertEqual(certificate["current_requested_total"], 101)

    def test_next_drop_preserves_the_deliberate_spare_slot(self):
        _, env, obs = self.fixture()
        obs.private["inventories"] = [{"MILK": 1}]
        next_action = {"farmer": ["DROP"], "hands": [], "market": []}
        owner = self.scheduler(20, PASS, {21: next_action})
        predecessor, candidate = self.profiles(
            owner, obs, PASS, env.configuration, end=21
        )
        self.assertFalse(predecessor(()))
        self.assertFalse(candidate(()))
        self.assertEqual(
            rr.reserve_release_certificate(
                owner, obs, PASS, env.configuration
            )["reason"],
            "next_unit_can_deposit",
        )

    def test_next_place_preserves_the_deliberate_spare_slot(self):
        _, env, obs = self.fixture()
        next_action = {
            "farmer": ["PLACE", "COW"],
            "hands": [],
            "market": [],
        }
        owner = self.scheduler(20, PASS, {21: next_action})
        _, candidate = self.profiles(
            owner, obs, PASS, env.configuration, end=21
        )
        self.assertFalse(candidate(()))
        self.assertEqual(
            rr.reserve_release_certificate(
                owner, obs, PASS, env.configuration
            )["reason"],
            "next_unit_can_deposit",
        )

    def test_current_or_next_executable_purchase_preserves_reserve(self):
        cases = {
            "current": (
                {
                    "farmer": ["PASS"],
                    "hands": [],
                    "market": [["BUY_ANIMAL", "COW", 1]],
                },
                PASS,
                "current_market_can_deposit",
            ),
            "next": (
                PASS,
                {
                    "farmer": ["PASS"],
                    "hands": [],
                    "market": [["BUY_PRODUCT", "WHEAT", 1]],
                },
                "next_market_can_deposit",
            ),
        }
        for name, (base, next_action, reason) in cases.items():
            with self.subTest(name=name):
                _, env, obs = self.fixture()
                owner = self.scheduler(20, base, {21: next_action})
                certificate = rr.reserve_release_certificate(
                    owner, obs, base, env.configuration
                )
                self.assertFalse(certificate["eligible"])
                self.assertEqual(certificate["reason"], reason)

    def test_inactive_tail_purchase_never_becomes_an_unsafe_admission(self):
        _, env, obs = self.fixture()
        env.configuration.maxMarketOrdersPerTurn = 1
        next_action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["HIRE"], ["BUY_ANIMAL", "COW", 1]],
        }
        owner = self.scheduler(20, PASS, {21: next_action})
        predecessor, candidate = self.profiles(
            owner, obs, PASS, env.configuration, end=21
        )
        self.assertFalse(predecessor(()))
        self.assertFalse(candidate(()))
        self.assertTrue(
            rr.reserve_release_certificate(
                owner, obs, PASS, env.configuration
            )["eligible"]
        )

    def test_malformed_active_market_row_fails_closed(self):
        _, env, obs = self.fixture()
        next_action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": ["not-an-action-row"],
        }
        owner = self.scheduler(20, PASS, {21: next_action})
        certificate = rr.reserve_release_certificate(
            owner, obs, PASS, env.configuration
        )
        self.assertFalse(certificate["eligible"])
        self.assertEqual(certificate["reason"], "malformed_next_market")

    def test_non_24_turn_day_semantics_fail_closed(self):
        _, env, obs = self.fixture()
        env.configuration.turnsPerDay = 12
        owner = self.scheduler(20, PASS, {21: PASS})
        certificate = rr.reserve_release_certificate(
            owner, obs, PASS, env.configuration
        )
        self.assertFalse(certificate["eligible"])
        self.assertEqual(certificate["reason"], "unsupported_turns_per_day")

    def test_dynamic_unit_producer_state_fails_closed(self):
        _, env, obs = self.fixture()
        owner = self.scheduler(20, PASS, {21: PASS})
        owner.joint_producer_busy = True
        predecessor, candidate = self.profiles(
            owner, obs, PASS, env.configuration, end=21
        )
        self.assertFalse(predecessor(()))
        self.assertFalse(candidate(()))
        self.assertEqual(
            rr.reserve_release_certificate(
                owner, obs, PASS, env.configuration
            )["reason"],
            "dynamic_unit_producer_busy_or_unbound",
        )

    def test_route_checkpoint_and_day_boundary_fail_closed(self):
        cases = (
            (225, 226, "route_checkpoint"),
            (23, 24, "day_boundary"),
        )
        for now, next_step, reason in cases:
            with self.subTest(reason=reason):
                _, env, obs = self.fixture(step=now)
                owner = self.scheduler(now, PASS, {next_step: PASS})
                certificate = rr.reserve_release_certificate(
                    owner, obs, PASS, env.configuration
                )
                self.assertFalse(certificate["eligible"])
                self.assertEqual(certificate["reason"], reason)

    def test_certificate_and_feasibility_leave_inputs_and_route_unchanged(self):
        _, env, obs = self.fixture()
        owner = self.scheduler(20, PASS, {21: PASS})
        before_obs = copy.deepcopy(obs)
        before_base = copy.deepcopy(PASS)
        before_route = copy.deepcopy(owner.controller.R)
        rr.install()
        farm, private = s.post_units(obs, PASS, env.configuration)
        feasible = owner.receipt_profile(
            obs, PASS, farm, private, 21, "MILK", env.configuration
        )
        self.assertTrue(feasible(()))
        self.assertEqual(obs, before_obs)
        self.assertEqual(PASS, before_base)
        self.assertEqual(owner.controller.R, before_route)

    def test_install_is_idempotent_and_reaches_existing_frozen_subclass(self):
        predecessor = rr.predecessor_receipt_profile()
        rr.install()
        rr.install()
        self.assertTrue(rr.installed())
        self.assertIs(
            frozen_selected.FrozenSelected.receipt_profile,
            rr.guarded_receipt_profile,
        )
        rr.restore()
        self.assertFalse(rr.installed())
        self.assertIs(s.SellScheduler.receipt_profile, predecessor)

    def test_unknown_peer_patch_is_never_overwritten(self):
        predecessor = s.SellScheduler.receipt_profile

        def peer_patch(*args, **kwargs):
            raise AssertionError("sentinel")

        s.SellScheduler.receipt_profile = peer_patch
        try:
            with self.assertRaisesRegex(RuntimeError, "another owner"):
                rr.install()
            with self.assertRaisesRegex(RuntimeError, "unknown peer patch"):
                rr.restore()
            self.assertIs(s.SellScheduler.receipt_profile, peer_patch)
        finally:
            s.SellScheduler.receipt_profile = predecessor


if __name__ == "__main__":
    unittest.main()
