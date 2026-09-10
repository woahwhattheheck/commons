# SPDX-License-Identifier: Apache-2.0
"""T03 queue quotation and arithmetic contracts."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import opening_script as opening  # noqa: E402
from opening_script_test_support import observation  # noqa: E402


class QuoteTests(unittest.TestCase):
    def test_gemini_legacy_cost_is_882_not_502(self):
        quote = opening.quote_market(
            observation(), opening.SCRIPTS["gemini_legacy"][0]
        )
        self.assertEqual(quote["cost"], 882.0)
        self.assertEqual(quote["remaining"], 118.0)

    def test_leader_legacy_cost_is_1507_and_infeasible(self):
        quote = opening.quote_market(
            observation(step=1), opening.SCRIPTS["leader_legacy"][1]
        )
        self.assertEqual(quote["cost"], 1507.0)
        self.assertEqual(quote["remaining"], -507.0)
        self.assertEqual(
            [line["cost"] for line in quote["orders"][:4]],
            [1.0, 1.0, 2.0, 3.0],
        )

    def test_hires_continue_from_public_hires_today(self):
        quote = opening.quote_market(
            observation(hires_today=3), [["HIRE"], ["HIRE"], ["HIRE"]]
        )
        self.assertEqual(
            [line["cost"] for line in quote["orders"]], [3.0, 5.0, 8.0]
        )

    def test_buy_product_requires_engine_curve_quote(self):
        with self.assertRaises(ValueError):
            opening.quote_market(
                observation(prices={"MILK": 160}), [["BUY_PRODUCT", "MILK", 2]]
            )

    def test_multiple_land_orders_walk_fixed_price_sequence(self):
        quote = opening.quote_market(
            observation(money=10000), [["BUY_LAND"], ["BUY_LAND"], ["BUY_LAND"]]
        )
        self.assertEqual(
            [line["cost"] for line in quote["orders"]],
            [1000.0, 2000.0, 4000.0],
        )
        self.assertEqual(quote["cost"], 7000.0)

    def test_sell_receipt_is_not_credited(self):
        quote = opening.quote_market(
            observation(money=10),
            [["SELL", "WHEAT", 100], ["BUY_SEED", "WHEAT", 2]],
        )
        self.assertEqual(quote["cost"], 20.0)
        self.assertEqual(quote["remaining"], -10.0)

    def test_string_unlocked_quadrants_is_rejected(self):
        obs = observation(money=10000)
        obs["farms"][0]["unlocked_quadrants"] = "NW"
        with self.assertRaises(ValueError):
            opening.quote_market(obs, [["BUY_LAND"]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
