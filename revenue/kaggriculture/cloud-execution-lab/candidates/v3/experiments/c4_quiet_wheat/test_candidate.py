from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import candidate as c4

r04 = c4.r04


def action(rows=0):
    return {
        "farmer": ["PASS"],
        "hands": [],
        "market": [["SELL", "MILK", 1] for _ in range(rows)],
    }


def tape_with(due_step, market):
    tape = [
        {"farmer": ["PASS"], "hands": [], "market": []}
        for _ in range(r04.LAST_STEP + 1)
    ]
    tape[due_step]["market"] = copy.deepcopy(market)
    return tape


class C4Tests(unittest.TestCase):
    def setUp(self):
        c4._CURRENT_SHOPS = ()
        r04.SALE_HORIZON = 8
        r04.SALE_EXCLUDED = ("WHEAT",)

    def test_center_tick_blocks(self):
        self.assertTrue(c4.crosses_public_wheat_demand(312, 313, ()))
        self.assertFalse(c4.crosses_public_wheat_demand(313, 314, ()))

    def test_wheat_shop_tick_blocks(self):
        self.assertTrue(c4.crosses_public_wheat_demand(316, 318, ("BAKERY",)))
        self.assertFalse(c4.crosses_public_wheat_demand(317, 318, ("BAKERY",)))
        self.assertFalse(c4.crosses_public_wheat_demand(316, 318, ("YARN_STORE",)))

    def test_lower_row_count_keeps_wheat_visible(self):
        tape = tape_with(302, [["SELL", "WHEAT", 3], ["SELL", "MILK", 1]])
        shadow = c4._filtered_tape(action(0), tape, 301)
        self.assertEqual(shadow[302]["market"], tape[302]["market"])

    def test_not_quieter_hides_only_wheat(self):
        tape = tape_with(302, [["SELL", "WHEAT", 3], ["SELL", "MILK", 1]])
        shadow = c4._filtered_tape(action(2), tape, 301)
        self.assertEqual(shadow[302]["market"], [["SELL", "MILK", 1]])
        self.assertEqual(tape[302]["market"][0], ["SELL", "WHEAT", 3])

    def test_public_demand_hides_only_wheat(self):
        c4._CURRENT_SHOPS = ("BAKERY",)
        tape = tape_with(317, [["SELL", "WHEAT", 3], ["SELL", "MILK", 1]])
        shadow = c4._filtered_tape(action(0), tape, 316)
        self.assertEqual(shadow[317]["market"], [["SELL", "MILK", 1]])

    def test_nonwheat_tape_is_exact_identity_objects(self):
        tape = tape_with(302, [["SELL", "MILK", 3]])
        shadow = c4._filtered_tape(action(0), tape, 301)
        self.assertIs(shadow[302], tape[302])

    def test_reserve_restores_exclusion(self):
        old = c4._BASE_RESERVE
        seen = []

        def fake(*args, **kwargs):
            seen.append(r04.SALE_EXCLUDED)

        c4._BASE_RESERVE = fake
        try:
            r04.SALE_EXCLUDED = ("WHEAT",)
            c4.reserve_sales_c4(action(0), object(), object(), tape_with(302, []), 301)
            self.assertEqual(seen, [()])
            self.assertEqual(r04.SALE_EXCLUDED, ("WHEAT",))
        finally:
            c4._BASE_RESERVE = old

    def test_reserve_restores_exclusion_on_error(self):
        old = c4._BASE_RESERVE

        def boom(*args, **kwargs):
            raise RuntimeError("x")

        c4._BASE_RESERVE = boom
        try:
            r04.SALE_EXCLUDED = ("WHEAT",)
            with self.assertRaises(RuntimeError):
                c4.reserve_sales_c4(action(0), object(), object(), tape_with(302, []), 301)
            self.assertEqual(r04.SALE_EXCLUDED, ("WHEAT",))
        finally:
            c4._BASE_RESERVE = old

    def test_disabled_returns_live_base_without_c4_hook(self):
        base = c4.install(enabled=False)
        self.assertIs(base, r04.v3_agent)
        self.assertIs(r04.reserve_sales, c4._BASE_RESERVE)
        self.assertEqual(r04.SALE_HORIZON, 8)
        self.assertEqual(r04.OPEN_ROUNDTRIP, 0)
        self.assertIs(r04.ROW_ORDER, True)
        self.assertIs(r04.EVENING_FLUSH, True)
        self.assertEqual(r04.SALE_EXCLUDED, ("WHEAT",))
        self.assertIs(r04._V231_EARLY, True)


if __name__ == "__main__":
    unittest.main()
