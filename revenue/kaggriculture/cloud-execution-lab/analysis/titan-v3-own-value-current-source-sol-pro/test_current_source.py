# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest

import verify_current_source as verifier

CASE = Path(__file__).resolve().parent
LAB = CASE.parents[1]
SOURCE = LAB / "selected_sell_core.py"
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

_spec = importlib.util.spec_from_file_location(
    "_titan_own_value_integrated_selected_sell_core", SOURCE
)
if _spec is None or _spec.loader is None:
    raise ImportError(f"cannot load {SOURCE}")
CORE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CORE)


class SourceBindingTests(unittest.TestCase):
    def test_real_source_satisfies_one_factor_contract(self) -> None:
        report = verifier.verify_source(SOURCE)
        self.assertTrue(report["one_factor_source_contract"])
        self.assertEqual(report["objective_field"], "own_cash + carry")
        self.assertEqual(
            report["diagnostic_fields"],
            ["own_cash", "other_cash", "remaining"],
        )
        self.assertEqual(report["objective_dependencies"], ["carry", "own_cash"])
        self.assertGreaterEqual(report["optimizer_score_calls"], 4)
        self.assertFalse(report["promotion_authorized"])

    def _rejects(self, source: str, pattern: str) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "selected_sell_core.py"
            path.write_text(textwrap.dedent(source), encoding="utf-8")
            with self.assertRaisesRegex(verifier.SourceContractError, pattern):
                verifier.verify_source(path)

    def test_predecessor_rival_subtraction_is_rejected(self) -> None:
        self._rejects(
            """
            class MarketPath:
                def score(self, plan, quantity, rival, alignment, terminal=False):
                    return own_cash + carry - other_cash, own_cash, other_cash, remaining
            def optimize_lot():
                pass
            """,
            "field 0 drift",
        )

    def test_diagnostic_tuple_drift_is_rejected(self) -> None:
        self._rejects(
            """
            class MarketPath:
                def score(self, plan, quantity, rival, alignment, terminal=False):
                    return own_cash + carry, own_cash, remaining, other_cash
            def optimize_lot():
                pass
            """,
            "field 2 drift",
        )

    def test_signature_drift_is_rejected(self) -> None:
        self._rejects(
            """
            class MarketPath:
                def score(self, plan, quantity, rival, alignment):
                    return own_cash + carry, own_cash, other_cash, remaining
            def optimize_lot():
                pass
            """,
            "parameter drift",
        )

    def test_duplicate_score_seam_is_rejected(self) -> None:
        self._rejects(
            """
            class MarketPath:
                def score(self, plan, quantity, rival, alignment, terminal=False):
                    return own_cash + carry, own_cash, other_cash, remaining
                def score(self, plan, quantity, rival, alignment, terminal=False):
                    return own_cash + carry, own_cash, other_cash, remaining
            def optimize_lot():
                pass
            """,
            "exactly one MarketPath.score",
        )


class IntegratedMechanismTests(unittest.TestCase):
    @staticmethod
    def model(joint, single=None):
        model = object.__new__(CORE.MarketPath)
        model.item = "FERTILIZER"
        model.inventory = 7
        model.params = {}
        model.shops = ()
        model.config = {}
        model.now = 0
        model.end = 0
        model.joint = joint
        model.single = single or (lambda inv, quantity: (0, inv))
        return model

    def test_rival_receipts_remain_diagnostics_not_objective(self) -> None:
        model = self.model(
            lambda inv, own, rival, alignment: (40, rival * 3, inv)
        )
        no_rival = model.score(((0, 1),), 1, 0, "paired", terminal=True)
        rival = model.score(((0, 1),), 1, 10, "paired", terminal=True)
        self.assertEqual(no_rival, (40, 40, 0, 0))
        self.assertEqual(rival, (40, 40, 30, 0))
        self.assertEqual(no_rival[0], rival[0])

    def test_continuation_value_is_included_without_tuple_drift(self) -> None:
        model = self.model(
            lambda inv, own, rival, alignment: (10, 3, inv),
            single=lambda inv, quantity: (7, inv),
        )
        self.assertEqual(
            model.score(((0, 1),), 2, 1, "paired", terminal=False),
            (17.0, 10, 3, 1),
        )
        self.assertEqual(
            model.score(((0, 1),), 2, 1, "paired", terminal=True),
            (10.0, 10, 3, 1),
        )

    def test_predecessor_inversion_now_selects_more_own_cash(self) -> None:
        receipts = {
            1: (100, 0),
            2: (112, 30),
        }
        model = self.model(
            lambda inv, own, rival, alignment: (*receipts[own], inv)
        )
        suppression = ((0, 1),)
        own_cash = ((0, 2),)
        scores = {
            suppression: model.score(suppression, 2, 0, "paired"),
            own_cash: model.score(own_cash, 2, 0, "paired"),
        }
        self.assertEqual(scores[suppression], (100.0, 100, 0, 1))
        self.assertEqual(scores[own_cash], (112, 112, 30, 0))
        selected = max(scores, key=lambda plan: scores[plan][0])
        self.assertEqual(selected, own_cash)
        self.assertEqual(scores[selected][1], 112)

    def test_terminal_objective_never_subtracts_rival_cash(self) -> None:
        model = self.model(
            lambda inv, own, rival, alignment: (25, 9, inv),
            single=lambda inv, quantity: (999, inv),
        )
        score = model.score(((0, 1),), 2, 5, "paired", terminal=True)
        self.assertEqual(score, (25.0, 25, 9, 1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
