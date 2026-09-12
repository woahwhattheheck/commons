# SPDX-License-Identifier: Apache-2.0
"""Historical V3.1 parity: real row-shed runs after terminal liquidation."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

SPEC = importlib.util.spec_from_file_location("_row_shed_terminal_parity_main", HERE / "main.py")
main = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(main)


class RowShedTerminalParityTests(unittest.TestCase):
    def test_terminal_liquidation_runs_real_donor_on_executable_prefix(self):
        import titan_runtime

        instance = main._new_instance(HERE, {"row_shed": True})
        instance.diagnostics = {"status": "completed"}
        selected = {
            "farmer": ["PASS", {"keep": "exact"}],
            "hands": [["PASS"], ["MOVE", "WEST"]],
            "market": [
                ["SELL", "WOOL", 10, {"row": "wool"}],
                ["SELL", "MILK", 10, {"row": "milk"}],
                ["SELL", "EGG", 99, {"suffix": "beyond-prefix"}],
                ["BUY_PRODUCT", "FERTILIZER", 1, {"suffix": "also-exact"}],
            ],
        }
        original = deepcopy(selected)
        obs = {
            "step": 718,
            "player": 0,
            "market": {"inventory": {"WOOL": 10000, "MILK": 10000}},
        }
        cfg = {"episodeSteps": 720, "maxMarketOrdersPerTurn": 2}

        def identity(_self, _obs, _cfg, action):
            return action

        scheduler = types.ModuleType("scheduler")
        def post_units(_obs, action, _cfg):
            self.assertEqual(action, original)
            return {}, {"shed": {"WOOL": 10, "MILK": 10}}
        scheduler.post_units = post_units

        with mock.patch.object(titan_runtime.TitanAgent, "_early_capital_selected", identity), \
                mock.patch.object(titan_runtime.TitanAgent, "_market_pressure_selected", identity), \
                mock.patch.dict(sys.modules, {"scheduler": scheduler}):
            returned = instance._early_capital_selected(obs, cfg, selected)

        # Actual canonical donor semantics: at equal public inventory/quantity,
        # MILK's next ten units depress its curve more than WOOL's, so the two
        # executable terminal SELL rows swap. Engine-inert suffix bytes do not.
        self.assertEqual(returned["market"][:2], [
            original["market"][1], original["market"][0]
        ])
        self.assertEqual([row[2] for row in returned["market"][:2]], [10, 10])
        self.assertEqual(returned["market"][2:], original["market"][2:])
        self.assertEqual(returned["farmer"], original["farmer"])
        self.assertEqual(returned["hands"], original["hands"])
        self.assertEqual(selected, original)
        self.assertEqual(instance.diagnostics["row_shed"]["status"], "applied")
        self.assertTrue(instance.diagnostics["row_shed"]["returned_action_bound"])
        self.assertEqual(instance._finalizer_checkpoint["stage"], "row_shed")
        self.assertEqual(instance._finalizer_checkpoint["action"], returned)


if __name__ == "__main__":
    unittest.main()
