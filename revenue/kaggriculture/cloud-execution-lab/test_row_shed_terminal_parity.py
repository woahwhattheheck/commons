# SPDX-License-Identifier: Apache-2.0
"""Historical V3.1 parity: row-shed still runs after terminal liquidation."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

SPEC = importlib.util.spec_from_file_location("_row_shed_terminal_parity_main", HERE / "main.py")
main = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(main)


class RowShedTerminalParityTests(unittest.TestCase):
    def test_terminal_liquidation_still_runs_final_row_shed(self):
        import titan_runtime

        instance = main._new_instance(HERE, {"row_shed": True})
        instance.diagnostics = {"status": "completed"}
        selected = {
            "farmer": ["PASS"],
            "hands": [["PASS"]],
            "market": [["SELL", "WOOL", 10], ["SELL", "MILK", 10]],
        }
        marked = deepcopy(selected)
        marked["market"] = list(reversed(marked["market"]))

        def identity(_self, _obs, _cfg, action):
            return action

        with mock.patch.object(titan_runtime.TitanAgent, "_early_capital_selected", identity), \
                mock.patch.object(titan_runtime.TitanAgent, "_market_pressure_selected", identity), \
                mock.patch.object(instance, "_row_shed_final_selected", return_value=marked) as row_shed:
            returned = instance._early_capital_selected(
                {"step": 718, "player": 0}, {"episodeSteps": 720}, selected
            )

        row_shed.assert_called_once_with(
            {"step": 718, "player": 0}, {"episodeSteps": 720}, selected
        )
        self.assertEqual(returned, marked)
        self.assertEqual(instance._finalizer_checkpoint["stage"], "row_shed")
        self.assertEqual(instance._finalizer_checkpoint["action"], marked)


if __name__ == "__main__":
    unittest.main()
