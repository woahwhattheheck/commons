# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
V3 = HERE.parents[1]
OVERLAY = V3 / "overlay"
for path in (HERE, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import r04_row_shed as row_shed  # noqa: E402
import r04_full_router as r04  # noqa: E402


class RowShedContract(unittest.TestCase):
    def test_requested_thousand_is_ranked_by_actual_stock(self):
        market = [
            ["SELL", "MELON", 1000],
            ["SELL", "WOOL", 50],
            ["HIRE"],
            ["SELL", "MILK", 3],
        ]
        # Incumbent R04 ranks raw requested quantity, so the 1000-unit tape dump wins.
        self.assertEqual(r04.order_sells(market, {})[0], ["SELL", "MELON", 1000])

        ordered = row_shed.order_leading_sells(
            market, {}, {"MELON": 1, "WOOL": 50}, r04._ro_price
        )
        # S33 row-shed prices only executable stock: 1 MELON vs 50 WOOL.
        self.assertEqual(ordered[:2], [["SELL", "WOOL", 50], ["SELL", "MELON", 1000]])
        self.assertEqual(ordered[2:], [["HIRE"], ["SELL", "MILK", 3]])
        self.assertEqual(sorted(map(repr, ordered[:2])), sorted(map(repr, market[:2])))

    def test_effective_quantity_is_min_requested_and_projected(self):
        self.assertEqual(row_shed.effective_sell_quantity(["SELL", "MILK", 1000], {"MILK": 8}), 8)
        self.assertEqual(row_shed.effective_sell_quantity(["SELL", "MILK", 4], {"MILK": 8}), 4)
        self.assertEqual(row_shed.effective_sell_quantity(["SELL", "MILK", 4], {}), 0)

    def test_equal_scores_keep_incumbent_order(self):
        market = [["SELL", "MILK", 1000], ["SELL", "WOOL", 1000], ["HIRE"]]
        ordered = row_shed.order_leading_sells(market, {}, {}, r04._ro_price)
        self.assertEqual(ordered, market)

    def test_only_contiguous_leading_sell_block_can_move(self):
        market = [["SELL", "MELON", 1000], ["SELL", "WOOL", 50], [], ["SELL", "MILK", 1000]]
        ordered = row_shed.order_leading_sells(
            market, {}, {"MELON": 1, "WOOL": 50, "MILK": 1000}, r04._ro_price
        )
        self.assertEqual(ordered[2:], market[2:])
        self.assertEqual(ordered[:2], [["SELL", "WOOL", 50], ["SELL", "MELON", 1000]])

    def test_malformed_quantity_fails_closed(self):
        for bad in (True, 3.0, "3", -1, None):
            with self.subTest(bad=bad):
                market = [["SELL", "MELON", 1000], ["SELL", "WOOL", bad], ["HIRE"]]
                self.assertIs(
                    row_shed.order_leading_sells(market, {}, {"MELON": 5, "WOOL": 5}, r04._ro_price),
                    market,
                )

    def test_malformed_projected_stock_fails_closed(self):
        market = [["SELL", "MELON", 1000], ["SELL", "WOOL", 50]]
        for bad in (True, 3.0, "3", -1, None):
            with self.subTest(bad=bad):
                self.assertIs(
                    row_shed.order_leading_sells(market, {}, {"MELON": 5, "WOOL": bad}, r04._ro_price),
                    market,
                )

    def test_nondefault_or_failed_price_model_fails_closed(self):
        market = [["SELL", "MELON", 1000], ["SELL", "WOOL", 50]]
        def broken(*_args):
            raise RuntimeError("no trusted default curve")
        self.assertIs(row_shed.order_leading_sells(market, {}, {"MELON": 5, "WOOL": 5}, broken), market)


if __name__ == "__main__":
    unittest.main()
