# SPDX-License-Identifier: Apache-2.0
"""Focused source contracts for the S33 row-shed ROW_ORDER repair."""

import ast
from pathlib import Path
import unittest


V3 = Path(__file__).resolve().parents[2]
TARGET = V3 / "overlay" / "r04_full_router.py"


def _load_row_order():
    source = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(TARGET))
    wanted_assigns = {"_RO_PARAMS", "_RO_I0"}
    wanted_funcs = {"_ro_shape", "_ro_price", "order_sells"}
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {t.id for t in node.targets if isinstance(t, ast.Name)}
            if names & wanted_assigns:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted_funcs:
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module)
    ns = {}
    exec(compile(module, str(TARGET), "exec"), ns)
    return source, ns["order_sells"]


class RowShedRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source, cls.order_sells = _load_row_order()

    def test_v3_agent_passes_projected_shed_to_row_order(self):
        self.assertIn("shed = projected_shed(action, FarmView(observation))", self.source)
        self.assertIn("ordered = order_sells(market, inventory, shed)", self.source)

    def test_legacy_two_argument_call_keeps_requested_quantity_scoring(self):
        market = [["SELL", "WHEAT", 1000], ["SELL", "CARROT", 10], ["HIRE"]]
        inventory = {"WHEAT": 10000, "CARROT": 10000}
        ordered = self.order_sells(market, inventory)
        self.assertEqual(ordered[0], ["SELL", "WHEAT", 1000])

    def test_projected_shed_clamps_impossible_oversized_row(self):
        market = [["SELL", "WHEAT", 1000], ["SELL", "CARROT", 10], ["HIRE"]]
        inventory = {"WHEAT": 10000, "CARROT": 10000}
        shed = {"WHEAT": 10, "CARROT": 10}
        ordered = self.order_sells(market, inventory, shed)
        self.assertEqual(ordered[:2], [["SELL", "CARROT", 10], ["SELL", "WHEAT", 1000]])
        self.assertEqual(ordered[2], ["HIRE"])

    def test_zero_sellable_stock_cannot_outrank_real_sale(self):
        market = [["SELL", "WHEAT", 1000], ["SELL", "CARROT", 10]]
        inventory = {"WHEAT": 10000, "CARROT": 10000}
        shed = {"WHEAT": 0, "CARROT": 10}
        ordered = self.order_sells(market, inventory, shed)
        self.assertEqual(ordered[0], ["SELL", "CARROT", 10])

    def test_only_leading_sell_block_moves_and_quantities_are_unchanged(self):
        market = [
            ["SELL", "WHEAT", 1000],
            ["SELL", "CARROT", 10],
            ["HIRE"],
            ["SELL", "WOOL", 5],
        ]
        inventory = {"WHEAT": 10000, "CARROT": 10000, "WOOL": 10000}
        shed = {"WHEAT": 10, "CARROT": 10, "WOOL": 5}
        ordered = self.order_sells(market, inventory, shed)
        self.assertEqual(ordered[2:], market[2:])
        self.assertCountEqual(ordered[:2], market[:2])


if __name__ == "__main__":
    unittest.main()
