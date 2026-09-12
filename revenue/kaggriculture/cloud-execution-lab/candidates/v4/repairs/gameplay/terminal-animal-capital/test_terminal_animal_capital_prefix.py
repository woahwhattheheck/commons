# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import unittest

from terminal_animal_capital import apply_terminal_animal_capital, plan_terminal_animal_capital


BASE = {"turnsPerDay": 24, "episodeSteps": 720}


def action(*rows):
    return {"farmer": ["PASS"], "hands": [], "market": list(rows)}


class H5ExecutablePrefixTests(unittest.TestCase):
    def test_default_limit_preserves_and_ignores_nonexecuted_dead_suffix(self):
        rows = [["SELL", "WHEAT", 1] for _ in range(10)]
        rows.append(["BUY_ANIMAL", "COW", 1])
        a = action(*rows)
        plan = plan_terminal_animal_capital(a, {"step": 648}, BASE)
        self.assertFalse(plan["eligible"])
        self.assertEqual(plan["reason"], "NO_PROVABLY_DEAD_ANIMAL_CAPITAL")
        self.assertIs(apply_terminal_animal_capital(a, {"step": 648}, BASE, enabled=True), a)

    def test_custom_limit_drops_only_executable_dead_row_and_preserves_suffix(self):
        cfg = {**BASE, "maxMarketOrdersPerTurn": 1}
        suffix = ["BUY_SEED", "WHEAT", 999]
        a = action(["BUY_ANIMAL", "GOOSE", 1], suffix)
        plan = plan_terminal_animal_capital(a, {"step": 648}, cfg)
        self.assertTrue(plan["eligible"])
        self.assertEqual(plan["drop_indices"], [0])
        self.assertEqual(plan["max_market_orders"], 1)
        out = apply_terminal_animal_capital(a, {"step": 648}, cfg, enabled=True)
        self.assertEqual(out["market"], [[], suffix])
        self.assertEqual(a["market"], [["BUY_ANIMAL", "GOOSE", 1], suffix])

    def test_nonexecuted_protected_suffix_does_not_block_executable_drop(self):
        cfg = {**BASE, "maxMarketOrdersPerTurn": 1}
        a = action(["BUY_ANIMAL", "SHEEP", 1], ["HIRE", 1])
        plan = plan_terminal_animal_capital(a, {"step": 648}, cfg)
        self.assertTrue(plan["eligible"])
        self.assertEqual(plan["drop_indices"], [0])

    def test_nonexecuted_malformed_suffix_is_opaque_and_preserved(self):
        cfg = {**BASE, "maxMarketOrdersPerTurn": 1}
        malformed = {"not": "an executable market row"}
        a = action(["BUY_ANIMAL", "COW", 1], malformed)
        out = apply_terminal_animal_capital(a, {"step": 648}, cfg, enabled=True)
        self.assertEqual(out["market"], [[], malformed])

    def test_executable_protected_row_still_blocks(self):
        cfg = {**BASE, "maxMarketOrdersPerTurn": 2}
        a = action(["BUY_ANIMAL", "GOOSE", 1], ["HIRE", 1])
        plan = plan_terminal_animal_capital(a, {"step": 648}, cfg)
        self.assertFalse(plan["eligible"])
        self.assertEqual(plan["reason"], "DOWNSTREAM_AFFORDABILITY_AMBIGUITY")

    def test_explicit_bad_market_limit_fails_closed(self):
        a = action(["BUY_ANIMAL", "GOOSE", 1])
        for value in (True, 1.0, "10", 0, -1):
            with self.subTest(value=value):
                cfg = {**BASE, "maxMarketOrdersPerTurn": value}
                self.assertIs(apply_terminal_animal_capital(a, {"step": 648}, cfg, enabled=True), a)


if __name__ == "__main__":
    unittest.main()
