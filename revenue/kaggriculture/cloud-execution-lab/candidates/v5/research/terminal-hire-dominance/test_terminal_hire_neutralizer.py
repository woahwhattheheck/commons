# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

from terminal_hire_neutralizer import transform


def action(*, market=None):
    return {
        "farmer": ["PASS"],
        "hands": [],
        "market": [] if market is None else copy.deepcopy(market),
    }


class TerminalHireNeutralizerTests(unittest.TestCase):
    def test_default_off_is_value_identity_and_input_immutable(self):
        selected = action(market=[["HIRE"], ["SELL", "MILK", 1]])
        before = copy.deepcopy(selected)
        result, report = transform({"step": 718}, None, selected)
        self.assertEqual(result, before)
        self.assertEqual(selected, before)
        self.assertFalse(report["changed"])
        self.assertEqual(report["reason"], "OFF")

    def test_exact_bool_flag(self):
        with self.assertRaises(TypeError):
            transform({"step": 718}, None, action(), enabled=1)

    def test_step717_is_untouched(self):
        selected = action(market=[["HIRE"], ["SELL", "MILK", 1]])
        result, report = transform({"step": 717}, None, selected, enabled=True)
        self.assertEqual(result, selected)
        self.assertEqual(report["reason"], "NONTERMINAL")

    def test_terminal_hires_become_noops_without_reindexing(self):
        selected = action(market=[
            ["HIRE"],
            ["SELL", "MILK", 1],
            ["HIRE"],
            ["BUY_PRODUCT", "WHEAT", 2],
        ])
        result, report = transform({"step": 718}, None, selected, enabled=True)
        self.assertEqual(result["market"], [
            [],
            ["SELL", "MILK", 1],
            [],
            ["BUY_PRODUCT", "WHEAT", 2],
        ])
        self.assertEqual(report["neutralized_indices"], [0, 2])
        self.assertEqual(len(result["market"]), len(selected["market"]))
        self.assertTrue(report["changed"])

    def test_custom_episode_terminal_is_exact(self):
        selected = action(market=[["HIRE"]])
        before, _ = transform(
            {"step": 8}, {"episodeSteps": 11}, selected, enabled=True
        )
        at_last, report = transform(
            {"step": 9}, {"episodeSteps": 11}, selected, enabled=True
        )
        self.assertEqual(before, selected)
        self.assertEqual(at_last["market"], [[]])
        self.assertEqual(report["terminal_step"], 9)

    def test_malformed_inputs_fail_closed(self):
        malformed = {"farmer": ["PASS"], "hands": [], "market": "bad"}
        result, report = transform({"step": 718}, None, malformed, enabled=True)
        self.assertEqual(result, malformed)
        self.assertTrue(report["reason"].startswith("FAIL_CLOSED:"))

    def test_no_terminal_hire_is_identity(self):
        selected = action(market=[["SELL", "MILK", 1]])
        result, report = transform({"step": 718}, None, selected, enabled=True)
        self.assertEqual(result, selected)
        self.assertFalse(report["changed"])
        self.assertEqual(report["reason"], "NO_TERMINAL_HIRE")


if __name__ == "__main__":
    unittest.main()
