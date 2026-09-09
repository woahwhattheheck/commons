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
        self.calls = []

    def score(self, plan, quantity, rival, alignment, terminal=False):
        self.calls.append((plan, quantity, rival, alignment, terminal))
        sold = min(
            int(quantity),
            sum(max(0, int(row[1])) for row in plan if len(row) > 1),
        )
        own_cash = 10 * sold
        rival_units = (
            sum(max(0, int(value)) for value in dict(rival).values())
            if isinstance(rival, tuple)
            else max(0, int(rival))
        )
        other_cash = 2 * rival_units
        remaining = int(quantity) - sold
        carry = 0.0 if terminal else 10.0 * remaining
        return own_cash + carry - other_cash, own_cash, other_cash, remaining


class LiquidityHaircutTests(unittest.TestCase):
    @staticmethod
    def module():
        return SimpleNamespace(MarketPath=BaseMarketPath)

    def test_exact_v1_factor_rewards_realized_cash_over_equal_full_carry(self):
        selected_core = self.module()
        receipt = install(selected_core)
        model = selected_core.MarketPath()
        held = model.score((), 4, 0, "paired")
        sold = model.score(((0, 1),), 4, 0, "paired")
        self.assertEqual(receipt["factor"], DEFAULT_CARRY_DISCOUNT)
        self.assertEqual(receipt["target"], "selected_sell_core.MarketPath")
        self.assertEqual(held, (38.0, 0, 0, 4))
        self.assertEqual(sold, (38.5, 10, 0, 3))
        self.assertGreater(sold[0], held[0])

    def test_wrapper_delegates_exact_inputs_and_preserves_noncarry_fields(self):
        selected_core = self.module()
        install(selected_core)
        model = selected_core.MarketPath()
        plan = ((1, 1),)
        rival = ((1, 3),)
        result = model.score(plan, 2, rival, "after")
        self.assertEqual(model.calls, [(plan, 2, rival, "after", False)])
        self.assertEqual(result, (13.5, 10, 6, 1))
        self.assertEqual(result[1:], (10, 6, 1))

    def test_terminal_and_fully_realized_scores_are_byte_semantically_unchanged(self):
        selected_core = self.module()
        install(selected_core)
        model = selected_core.MarketPath()
        terminal = model.score((), 4, 0, "paired", terminal=True)
        realized = model.score(((0, 4),), 4, 3, "paired")
        self.assertEqual(terminal, (0.0, 0, 0, 4))
        self.assertEqual(realized, (34.0, 40, 6, 0))

    def test_install_is_idempotent_and_rejects_conflicting_factor(self):
        selected_core = self.module()
        first = install(selected_core)
        installed = selected_core.MarketPath
        second = install(selected_core)
        self.assertTrue(first["installed"])
        self.assertTrue(second["idempotent"])
        self.assertIs(installed, selected_core.MarketPath)
        with self.assertRaises(RuntimeError):
            install(selected_core, discount=0.9)

    def test_invalid_factor_fails_closed(self):
        for factor in (0, -0.1, 1.01, math.nan, math.inf):
            with self.subTest(factor=factor), self.assertRaises(ValueError):
                install(self.module(), discount=factor)

    def test_selected_optimizer_module_observes_replacement(self):
        selected_core = self.module()
        selected_core.construct = lambda: selected_core.MarketPath()
        install(selected_core)
        made = selected_core.construct()
        self.assertEqual(
            getattr(type(made), "_sol_kepler_horizon_liquidity_discount"),
            0.95,
        )

    def test_candidate_installs_before_canonical_constructor(self):
        selected_core = self.module()
        prior = sys.modules.get("selected_sell_core")
        original = candidate._ORIGINAL_NEW_INSTANCE
        original_receipt = candidate._LAST_INSTALL_RECEIPT
        seen = []

        def constructor(root, feature_data):
            seen.append(
                getattr(
                    selected_core.MarketPath,
                    "_sol_kepler_horizon_liquidity_discount",
                    None,
                )
            )
            return SimpleNamespace()

        try:
            sys.modules["selected_sell_core"] = selected_core
            candidate._ORIGINAL_NEW_INSTANCE = constructor
            instance = candidate._candidate_new_instance(
                Path("/tmp/root"), {"consumer": "frozen"}
            )
        finally:
            receipt = dict(candidate._LAST_INSTALL_RECEIPT or {})
            candidate._ORIGINAL_NEW_INSTANCE = original
            candidate._LAST_INSTALL_RECEIPT = original_receipt
            if prior is None:
                sys.modules.pop("selected_sell_core", None)
            else:
                sys.modules["selected_sell_core"] = prior
        self.assertEqual(seen, [0.95])
        self.assertIsNotNone(instance)
        self.assertEqual(receipt["factor"], 0.95)
        self.assertEqual(receipt["target"], "selected_sell_core.MarketPath")

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

    def test_exact_source_seam_and_production_binding_are_attested(self):
        report = audit_change.build_report()
        self.assertEqual(report["decision"], "PASS")
        self.assertEqual(
            report["claim"]["target"], "selected_sell_core.MarketPath.score"
        )
        self.assertTrue(all(report["checks"].values()))


if __name__ == "__main__":
    unittest.main()
