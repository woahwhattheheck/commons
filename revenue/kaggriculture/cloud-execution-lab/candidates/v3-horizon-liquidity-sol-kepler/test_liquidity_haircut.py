# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import math
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

import audit_change
import candidate
from liquidity_haircut import DEFAULT_CARRY_DISCOUNT, install


class BaseMarketPath:
    def __init__(self):
        self.inventory = 0
        self.now = 0
        self.end = 1
        self.item = "MILK"
        self.shops = []
        self.config = {}
        self.rivals = []

    def single(self, inv, quantity):
        return 10 * quantity, inv

    def joint(self, inv, own, rival, alignment):
        self.rivals.append((own, rival, alignment))
        return 10 * own, 2 * rival, inv


class LiquidityHaircutTests(unittest.TestCase):
    @staticmethod
    def module():
        return SimpleNamespace(MarketPath=BaseMarketPath, absorption=lambda *_: 0)

    def test_exact_v1_factor_rewards_realized_cash_over_equal_modeled_carry(self):
        scheduler = self.module()
        receipt = install(scheduler)
        model = scheduler.MarketPath()
        held = model.score((), 4, 0, "paired")
        sold = model.score(((0, 1),), 4, 0, "paired")
        self.assertEqual(receipt["factor"], DEFAULT_CARRY_DISCOUNT)
        self.assertEqual(held, (38.0, 0, 0, 4))
        self.assertEqual(sold, (38.5, 10, 0, 3))
        self.assertGreater(sold[0], held[0])

    def test_terminal_inventory_is_not_credited(self):
        scheduler = self.module()
        install(scheduler)
        model = scheduler.MarketPath()
        self.assertEqual(model.score((), 4, 0, "paired", terminal=True), (0.0, 0, 0, 4))

    def test_delayed_rival_tuple_and_return_shape_are_preserved(self):
        scheduler = self.module()
        install(scheduler)
        model = scheduler.MarketPath()
        result = model.score(((1, 1),), 2, ((1, 3),), "paired")
        self.assertEqual(model.rivals, [(0, 0, "paired"), (1, 3, "paired")])
        self.assertEqual(result, (13.5, 10, 6, 1))

    def test_install_is_idempotent_and_rejects_conflicting_factor(self):
        scheduler = self.module()
        first = install(scheduler)
        installed = scheduler.MarketPath
        second = install(scheduler)
        self.assertTrue(first["installed"])
        self.assertTrue(second["idempotent"])
        self.assertIs(installed, scheduler.MarketPath)
        with self.assertRaises(RuntimeError):
            install(scheduler, discount=0.9)

    def test_invalid_factor_fails_closed(self):
        for factor in (0, -0.1, 1.01, math.nan, math.inf):
            with self.subTest(factor=factor), self.assertRaises(ValueError):
                install(self.module(), discount=factor)

    def test_candidate_installs_before_canonical_constructor(self):
        scheduler = self.module()
        prior_scheduler = sys.modules.get("scheduler")
        original = candidate._ORIGINAL_NEW_INSTANCE
        seen = []

        def constructor(root, feature_data):
            seen.append(getattr(scheduler.MarketPath, "_sol_kepler_horizon_liquidity_discount", None))
            return SimpleNamespace()

        try:
            sys.modules["scheduler"] = scheduler
            candidate._ORIGINAL_NEW_INSTANCE = constructor
            instance = candidate._candidate_new_instance(Path("/tmp/root"), {"consumer": "frozen"})
        finally:
            candidate._ORIGINAL_NEW_INSTANCE = original
            if prior_scheduler is None:
                sys.modules.pop("scheduler", None)
            else:
                sys.modules["scheduler"] = prior_scheduler
        self.assertEqual(seen, [0.95])
        self.assertEqual(instance.horizon_liquidity_receipt["factor"], 0.95)

    def test_candidate_delegates_outer_entrypoint_unchanged(self):
        original = candidate._CANONICAL.agent
        token = object()
        calls = []
        try:
            candidate._CANONICAL.agent = lambda observation, configuration=None: (
                calls.append((observation, configuration)) or token
            )
            result = candidate.agent({"step": 7}, {"episodeSteps": 720})
        finally:
            candidate._CANONICAL.agent = original
        self.assertIs(result, token)
        self.assertEqual(calls, [({"step": 7}, {"episodeSteps": 720})])

    def test_exact_source_seam_is_attested(self):
        report = audit_change.build_report()
        self.assertEqual(report["decision"], "PASS")
        self.assertTrue(all(report["checks"].values()))


if __name__ == "__main__":
    unittest.main()
