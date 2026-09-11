# SPDX-License-Identifier: Apache-2.0
"""H10 audit: predecessor killers for a naive final-output E11 port onto R04.

This is deliberately a *negative* experiment.  R04/E184 owns future-sale debt before its
final action is returned.  E11 was designed for the canonical seller seam before pending
accounting.  Applying E11 afterward can blank a SELL while leaving R04's already-recorded
debt intact, causing a future planned SELL to be subtracted even though the advanced SELL
never executed.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

OVERLAY = Path(__file__).resolve().parents[1] / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

from e11_rival_sell import apply_e11  # noqa: E402


def observation(*, step=200, price=5):
    return {
        "step": step,
        "player": 0,
        "market": {"prices": {"MILK": price}},
        "town": {"unlocked_shops": []},
    }


def exact_absorption(_item, _step, _shops, _config):
    # Integer, nonnegative engine-like tick; enough future capacity for E11 eligibility.
    return 1


class H10E11NoFinalPortTests(unittest.TestCase):
    def test_post_accounting_deferral_leaves_r04_debt_orphaned(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "MILK", 2]]}
        before = deepcopy(action)

        # This models state that E184 reserve_sales has already committed for the advanced
        # MILK row before its outer agent returns the action.  A final-output wrapper has no
        # ownership of this state and apply_e11 accepts no debt/unwind callback.
        r04_sale_window_debts = {205: {"MILK": 2}}
        debts_before = deepcopy(r04_sale_window_debts)

        out, report = apply_e11(
            observation(),
            action,
            [(199, {"MILK": 25})],
            {"episodeSteps": 720, "rival_dump_price_drop": 15, "e11_min_future_absorption": 2},
            exact_absorption,
            enabled=True,
        )

        self.assertTrue(report["changed"])
        self.assertEqual(report["deferred"], ["MILK"])
        self.assertEqual(out["market"], [[]])
        self.assertEqual(action, before)  # E11 itself remains copy-on-edit.
        self.assertEqual(r04_sale_window_debts, debts_before)  # dangerous orphaned debt

    def test_missing_exact_absorption_fails_closed(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "MILK", 2]]}
        out, report = apply_e11(
            observation(),
            action,
            [(199, {"MILK": 25})],
            {"episodeSteps": 720, "rival_dump_price_drop": 15, "e11_min_future_absorption": 2},
            None,
            enabled=True,
        )
        self.assertIs(out, action)
        self.assertFalse(report["changed"])
        self.assertEqual(report["reason"], "NO_OP_NO_ABSORPTION_FUNCTION")


if __name__ == "__main__":
    unittest.main(verbosity=2)
