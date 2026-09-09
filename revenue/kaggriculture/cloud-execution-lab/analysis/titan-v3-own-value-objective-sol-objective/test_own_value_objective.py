# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import math
from pathlib import Path
from types import SimpleNamespace
import unittest

import own_value_objective as objective


def bound_module():
    class MarketPath:
        def score(self, plan, quantity, rival, alignment, terminal=False):
            own_cash, carry, other_cash, remaining = plan
            return own_cash+carry-other_cash, own_cash,other_cash,remaining
    return SimpleNamespace(
        MarketPath=MarketPath,
        __file__="/tmp/selected_sell_core.py",
    )


def drifted_module():
    class MarketPath:
        def score(self, plan, quantity, rival, alignment, terminal=False):
            own_cash, carry, other_cash, remaining = plan
            return own_cash+carry, own_cash,other_cash,remaining
    return SimpleNamespace(
        MarketPath=MarketPath,
        __file__="/tmp/selected_sell_core.py",
    )


def wrong_signature_module():
    class MarketPath:
        def score(self, plan, quantity, rival, alignment):
            own_cash, carry, other_cash, remaining = plan
            return own_cash+carry-other_cash, own_cash,other_cash,remaining
    return SimpleNamespace(
        MarketPath=MarketPath,
        __file__="/tmp/selected_sell_core.py",
    )


class OwnValueTupleTests(unittest.TestCase):
    def test_recovers_realized_plus_carry(self):
        transformed = objective.own_value_tuple((82.0, 112, 30, 7))
        self.assertEqual(transformed, (112.0, 112, 30, 7))

    def test_rival_receipts_do_not_change_own_objective(self):
        a = objective.own_value_tuple((100.0, 100, 0, 0))
        b = objective.own_value_tuple((70.0, 100, 30, 0))
        self.assertEqual(a[0], b[0])

    def test_only_first_tuple_field_changes(self):
        original = (82.0, 112, 30, 7)
        transformed = objective.own_value_tuple(original)
        self.assertEqual(transformed[1:], original[1:])

    def test_rejects_malformed_tuple(self):
        with self.assertRaisesRegex(objective.ObjectiveScoreError, "four-tuple"):
            objective.own_value_tuple([1, 2, 3, 4])
        with self.assertRaisesRegex(objective.ObjectiveScoreError, "four-tuple"):
            objective.own_value_tuple((1, 2, 3))

    def test_rejects_nonfinite_and_boolean_values(self):
        for value in (math.nan, math.inf, True):
            with self.subTest(value=value):
                with self.assertRaises(objective.ObjectiveScoreError):
                    objective.own_value_tuple((value, 1, 0, 0))

    def test_rejects_negative_implied_carry(self):
        with self.assertRaisesRegex(objective.ObjectiveScoreError, "below realized"):
            objective.own_value_tuple((50.0, 100, 20, 0))


class InstallTests(unittest.TestCase):
    def test_install_is_one_factor_and_idempotent(self):
        module = bound_module()
        before = module.MarketPath.score
        receipt = objective.install(module=module)
        after = module.MarketPath.score
        self.assertIsNot(before, after)
        self.assertEqual(after(module.MarketPath(), (112, 0, 30, 7), 0, 0, "paired"),
                         (112.0, 112, 30, 7))
        self.assertEqual(objective.install(module=module), receipt)
        self.assertIs(module.MarketPath.score, after)
        self.assertFalse(receipt["canonical_files_modified"])

    def test_install_rejects_source_drift(self):
        with self.assertRaisesRegex(objective.ObjectiveBindingError, "source drift"):
            objective.install(module=drifted_module())

    def test_install_rejects_signature_drift(self):
        with self.assertRaisesRegex(objective.ObjectiveBindingError, "signature drift"):
            objective.install(module=wrong_signature_module())

    def test_install_rejects_wrong_source_path(self):
        module = bound_module()
        module.__file__ = "/tmp/not_the_core.py"
        with self.assertRaisesRegex(objective.ObjectiveBindingError, "selected_sell_core.py"):
            objective.install(module=module)

    def test_install_rejects_wrong_root(self):
        module = bound_module()
        with self.assertRaisesRegex(objective.ObjectiveBindingError, "path mismatch"):
            objective.install(module=module, expected_root=Path("/definitely/not/tmp"))

    def test_conflicting_patch_is_rejected(self):
        module = bound_module()
        setattr(module.MarketPath.score, "__titan_own_value_objective_version__", "other")
        with self.assertRaisesRegex(objective.ObjectiveBindingError, "conflicting"):
            objective.install(module=module)


if __name__ == "__main__":
    unittest.main()
