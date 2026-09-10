# SPDX-License-Identifier: Apache-2.0
"""Engine-prefix regression for frozen seller same-turn acquisition funding."""
from __future__ import annotations

import ast
import copy
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "frozen_selected.py"
ENGINE = HERE / "reference" / "engine" / "kaggriculture.py"


def load_subject():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    wanted = {"sale_quantities", "fund_same_turn_acquisition"}
    body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    if {node.name for node in body} != wanted:
        raise AssertionError("subject functions missing from frozen_selected.py")
    module = ast.Module(body=body, type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {"copy": copy}
    exec(compile(module, str(SOURCE), "exec"), namespace)
    namespace["_market_prefix_state"] = prefix_state
    return namespace["fund_same_turn_acquisition"]


def prefix_state(orders, farm, private, market, shops, config, now, rival_quantity, stop):
    """Exact fixed-price fixture for the order-prefix boundary under test."""
    del market, shops, config, now, rival_quantity
    money = int(farm["money"])
    shed = dict(private["shed"])
    outcomes = {}
    stress = []
    stop = min(int(stop), len(orders) - 1)
    for index, order in enumerate(orders[: stop + 1]):
        if not order:
            continue
        if order[0] == "SELL" and len(order) > 2 and order[1] == "CARROT":
            sold = min(max(0, int(order[2])), max(0, int(shed.get("CARROT", 0))))
            shed["CARROT"] = max(0, int(shed.get("CARROT", 0)) - sold)
            money += sold * 35
            stress.append(
                {
                    "index": index,
                    "item": "CARROT",
                    "quantity": sold,
                    "receipt": sold * 35,
                    "scenario": "fixed-price-fixture",
                }
            )
        elif order[0] == "BUY_PRODUCT":
            return {
                "money": money,
                "outcomes": outcomes,
                "unsupported_index": index,
                "shed": shed,
                "inventory": {},
                "sale_stress": stress,
            }
        elif order[0] == "BUY_LAND":
            completed = int(money >= 1000)
            if completed:
                money -= 1000
            outcomes[index] = {"required": 1, "completed": completed, "cost_per_unit": 1000}
    return {
        "money": money,
        "outcomes": outcomes,
        "unsupported_index": None,
        "shed": shed,
        "inventory": {},
        "sale_stress": stress,
    }


class FrozenActivePrefixFundingTest(unittest.TestCase):
    def setUp(self):
        self.subject = load_subject()
        self.farm = {"money": 900, "hires_today": 0, "unlocked_quadrants": ["NW"]}
        self.private = {"shed": {"CARROT": 3}}
        self.config = {"maxMarketOrdersPerTurn": 10}

    def call(self, orders):
        return self.subject(
            orders,
            self.farm,
            self.private,
            {"inventory": {"CARROT": 1000}},
            [],
            self.config,
            0,
            {"CARROT"},
            lambda _item: 0,
        )

    def test_off_prefix_target_cannot_activate_sale_only(self):
        orders = [[] for _ in range(10)] + [["BUY_LAND"], ["SELL", "CARROT", 3]]
        transformed, info = self.call(orders)
        self.assertEqual(transformed, orders)
        self.assertIsNone(info)
        self.assertFalse(any(row for row in transformed[:10]))

    def test_off_prefix_sale_cannot_fund_live_target(self):
        orders = [[] for _ in range(8)] + [["BUY_LAND"], [], ["SELL", "CARROT", 3]]
        transformed, info = self.call(orders)
        self.assertEqual(transformed, orders)
        self.assertEqual(info["reason"], "no-safe-prefix-sale")
        self.assertEqual(info["target_index"], 8)

    def test_live_prefix_sale_still_funds_live_target(self):
        orders = [[] for _ in range(8)] + [["BUY_LAND"], ["SELL", "CARROT", 3]]
        transformed, info = self.call(orders)
        self.assertTrue(info["applied"])
        self.assertEqual((info["source_index"], info["destination_index"]), (9, 7))
        self.assertEqual(transformed[7], ["SELL", "CARROT", 3])
        self.assertEqual(transformed[8], ["BUY_LAND"])
        state = prefix_state(
            transformed,
            self.farm,
            self.private,
            {},
            [],
            self.config,
            0,
            lambda _item: 0,
            9,
        )
        self.assertEqual(state["outcomes"][8]["completed"], 1)

    def test_reference_engine_truncates_queue_before_market_processing(self):
        source = ENGINE.read_text(encoding="utf-8")
        self.assertIn("queues.append(q[:max_orders])", source)


if __name__ == "__main__":
    unittest.main()
