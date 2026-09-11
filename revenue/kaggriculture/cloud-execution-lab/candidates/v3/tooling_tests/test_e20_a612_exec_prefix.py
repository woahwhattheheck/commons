#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Canonical-a612 predecessors for the reviewed E20 executable-prefix repair.

These are focused custody/mechanism tests.  They intentionally exercise only the
source theorem already reviewed in #12166/#12405: HIRE accounting and blanking
must be confined to the market prefix the pinned interpreter can execute, with
its minimum-one clamp for explicit zero/negative caps.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

V3 = Path(__file__).resolve().parents[1]
OVERLAY = V3 / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

import e20_hire_guard as e20  # noqa: E402


def observation(*, hires_today=0):
    return {
        "step": 10,
        "player": 0,
        "farms": [
            {"hires_today": hires_today, "tiles": [[{"kind": "PLANT", "watered_today": True}]]},
            {"hires_today": 0, "tiles": [[None]]},
        ],
    }


class E20ExecutablePrefix(unittest.TestCase):
    def test_tail_only_hire_beyond_standard_cap_is_exact_identity(self):
        action = {"market": [["SELL", "WHEAT", 1] for _ in range(10)] + [["HIRE"]]}
        before = deepcopy(action)
        out, report = e20.apply_hire_guard(
            observation(hires_today=3), action, {"maxMarketOrdersPerTurn": 10}, enabled=True
        )
        self.assertIs(out, action)
        self.assertEqual(out, before)
        self.assertEqual(report["reason"], "NO_HIRE")
        self.assertFalse(report["changed"])

    def test_tail_hire_does_not_consume_remaining_allowance(self):
        action = {"market": [["HIRE"]] + [["SELL", "WHEAT", 1] for _ in range(9)] + [["HIRE"]]}
        before = deepcopy(action)
        out, report = e20.apply_hire_guard(
            observation(hires_today=2), action, {"maxMarketOrdersPerTurn": 10}, enabled=True
        )
        self.assertIs(out, action)
        self.assertEqual(out, before)
        self.assertEqual(report["reason"], "HIRES_WITHIN_LOW_DEMAND_ALLOWANCE")
        self.assertFalse(report["changed"])

    def test_custom_prefix_drops_only_executable_excess_and_preserves_tail(self):
        action = {"market": [["HIRE"], ["SELL", "WHEAT", 1], ["HIRE"], ["HIRE"]]}
        original = deepcopy(action)
        out, report = e20.apply_hire_guard(
            observation(hires_today=2), action, {"maxMarketOrdersPerTurn": 3}, enabled=True
        )
        self.assertEqual(action, original)
        self.assertEqual(out["market"], [["HIRE"], ["SELL", "WHEAT", 1], [], ["HIRE"]])
        self.assertEqual(report["dropped_indices"], [2])
        self.assertTrue(report["changed"])

    def test_zero_cap_matches_interpreter_minimum_one(self):
        action = {"market": [["HIRE"], ["HIRE"]]}
        out, report = e20.apply_hire_guard(
            observation(hires_today=3), action, {"maxMarketOrdersPerTurn": 0}, enabled=True
        )
        self.assertEqual(out["market"], [[], ["HIRE"]])
        self.assertEqual(report["dropped_indices"], [0])

    def test_negative_cap_matches_interpreter_minimum_one(self):
        action = {"market": [["HIRE"], ["HIRE"]]}
        out, report = e20.apply_hire_guard(
            observation(hires_today=3), action, {"maxMarketOrdersPerTurn": -3}, enabled=True
        )
        self.assertEqual(out["market"], [[], ["HIRE"]])
        self.assertEqual(report["dropped_indices"], [0])


if __name__ == "__main__":
    unittest.main()
