# SPDX-License-Identifier: Apache-2.0
"""T03 exact-step admission, identity, and immutability contracts."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import opening_script as opening  # noqa: E402
from opening_script_test_support import action, observation  # noqa: E402


class ApplyTests(unittest.TestCase):
    def test_off_is_object_identity(self):
        inherited = action()
        out, report = opening.apply_opening_script(
            observation(), inherited, {}, enabled=False
        )
        self.assertIs(out, inherited)
        self.assertEqual(report["reason"], "OFF")

    def test_after_step_47_is_identity(self):
        inherited = action()
        out, report = opening.apply_opening_script(
            observation(step=48), inherited, {}, enabled=True
        )
        self.assertIs(out, inherited)
        self.assertEqual(report["reason"], "AFTER_OPENING_HORIZON")

    def test_canonical_variant_is_identity(self):
        inherited = action()
        out, report = opening.apply_opening_script(
            observation(), inherited,
            {"opening_script_variant": "canonical"}, enabled=True,
        )
        self.assertIs(out, inherited)
        self.assertEqual(report["reason"], "CANONICAL_IDENTITY")

    def test_balanced_is_admitted_and_preserves_nonmarket_actions(self):
        inherited = action()
        before = deepcopy(inherited)
        out, report = opening.apply_opening_script(
            observation(), inherited,
            {"opening_script_variant": "balanced", "opening_cash_reserve": 350},
            enabled=True,
        )
        self.assertEqual(inherited, before)
        self.assertIsNot(out, inherited)
        self.assertEqual(out["farmer"], inherited["farmer"])
        self.assertEqual(out["hands"], inherited["hands"])
        self.assertEqual(out["market"], opening.SCRIPTS["balanced"][0])
        self.assertEqual(report["quote"]["cost"], 402.0)
        self.assertEqual(report["quote"]["remaining"], 598.0)
        self.assertEqual(report["reason"], "OPENING_SCRIPT_APPLIED")

    def test_gemini_legacy_rejected_by_default_reserve(self):
        inherited = action()
        out, report = opening.apply_opening_script(
            observation(), inherited,
            {"opening_script_variant": "gemini_legacy"}, enabled=True,
        )
        self.assertIs(out, inherited)
        self.assertEqual(report["reason"], "SOLVENCY_REJECT")
        self.assertEqual(report["required_cash"], 1232.0)

    def test_leader_legacy_rejected_even_with_zero_reserve(self):
        inherited = action()
        out, report = opening.apply_opening_script(
            observation(step=1), inherited,
            {"opening_script_variant": "leader_legacy", "opening_cash_reserve": 0},
            enabled=True,
        )
        self.assertIs(out, inherited)
        self.assertEqual(report["reason"], "SOLVENCY_REJECT")
        self.assertEqual(report["required_cash"], 1507.0)

    def test_exact_step_only(self):
        inherited = action()
        out, report = opening.apply_opening_script(
            observation(step=1), inherited,
            {"opening_script_variant": "balanced"}, enabled=True,
        )
        self.assertIs(out, inherited)
        self.assertEqual(report["reason"], "NO_SCRIPT_AT_STEP")

    def test_already_scripted_is_object_identity(self):
        inherited = {
            "farmer": ["PASS"],
            "hands": [],
            "market": deepcopy(opening.SCRIPTS["balanced"][0]),
        }
        out, report = opening.apply_opening_script(
            observation(), inherited,
            {"opening_script_variant": "balanced"}, enabled=True,
        )
        self.assertIs(out, inherited)
        self.assertEqual(report["reason"], "ALREADY_SCRIPTED")

    def test_market_cap_failure_preserves_inherited_action(self):
        inherited = action()
        out, report = opening.apply_opening_script(
            observation(), inherited,
            {"opening_script_variant": "balanced", "maxMarketOrdersPerTurn": 3},
            enabled=True,
        )
        self.assertIs(out, inherited)
        self.assertEqual(report["reason"], "MARKET_QUEUE_CAP")

    def test_nonfinite_and_boolean_money_fail_closed(self):
        inherited = action()
        for money in (float("nan"), float("inf"), True):
            out, report = opening.apply_opening_script(
                observation(money=money), inherited,
                {"opening_script_variant": "balanced"}, enabled=True,
            )
            self.assertIs(out, inherited)
            self.assertEqual(report["reason"], "INVALID_SCRIPT")


if __name__ == "__main__":
    unittest.main(verbosity=2)
