import pathlib
import sys
import unittest
from types import SimpleNamespace

HERE = pathlib.Path(__file__).resolve().parent
OVERLAY = HERE.parent
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

import r04_d4_strawberry_timing as d4  # noqa: E402

base = d4.base


class View:
    def __init__(self, stock=12, price=200):
        self.shed = {item: 0 for item in base.PRODUCTS}
        self.shed["STRAWBERRY"] = stock
        self.prices = {"STRAWBERRY": price}
        self.positions = []
        self.inventories = []

    def inventory(self, actor):
        return {}

    def beside_shed(self, pos):
        return False


def action(market=None):
    return {"farmer": ["PASS"], "hands": [], "market": list(market or [])}


def tape_with(step, qty=1000, pickup_step=None):
    tape = [{"farmer": ["PASS"], "hands": [], "market": []}
            for _ in range(base.LAST_STEP + 1)]
    tape[step]["market"] = [["SELL", "STRAWBERRY", qty]]
    if pickup_step is not None:
        tape[pickup_step]["farmer"] = ["PICKUP", "STRAWBERRY", 1]
    return tape


class D4V4Tests(unittest.TestCase):
    def state(self, debts=None):
        return SimpleNamespace(queues={}, sale_window_debts={} if debts is None else debts)

    def test_feature_off_is_exact_identity(self):
        original = action()
        self.assertIs(
            d4.apply_d4_strawberry_timing(original, {}, enabled=False),
            original,
        )

    def test_preflush_authored_sale_can_advance(self):
        old_horizon, old_flush = base.SALE_HORIZON, base.EVENING_FLUSH
        base.SALE_HORIZON = 8
        base.EVENING_FLUSH = True
        try:
            state = self.state()
            out, added, reservations = d4.advance_midgame_strawberry(
                action(), View(stock=12, price=200), state, tape_with(380), 369,
            )
            self.assertEqual(12, added)
            self.assertEqual(((380, 12),), reservations)
            self.assertEqual([["SELL", "STRAWBERRY", 12]], out["market"])
            self.assertEqual({380: {"STRAWBERRY": 12}}, state.sale_window_debts)
        finally:
            base.SALE_HORIZON, base.EVENING_FLUSH = old_horizon, old_flush

    def test_incumbent_flush_owns_later_h22_row(self):
        old_horizon, old_flush = base.SALE_HORIZON, base.EVENING_FLUSH
        base.SALE_HORIZON = 8
        base.EVENING_FLUSH = True
        try:
            original = action()
            state = self.state()
            out, added, reservations = d4.advance_midgame_strawberry(
                original, View(stock=12, price=200), state, tape_with(382), 373,
            )
            self.assertIs(out, original)
            self.assertEqual((0, ()), (added, reservations))
            self.assertEqual({}, state.sale_window_debts)
        finally:
            base.SALE_HORIZON, base.EVENING_FLUSH = old_horizon, old_flush

    def test_price_threshold_is_fail_closed(self):
        original = action()
        state = self.state()
        out, added, reservations = d4.advance_midgame_strawberry(
            original, View(stock=12, price=d4.MIN_PRICE - 1), state, tape_with(402), 384,
        )
        self.assertIs(out, original)
        self.assertEqual((0, ()), (added, reservations))
        self.assertEqual({}, state.sale_window_debts)

    def test_current_strawberry_trade_is_parent_owned(self):
        original = action([["SELL", "STRAWBERRY", 2]])
        state = self.state()
        out, added, _ = d4.advance_midgame_strawberry(
            original, View(), state, tape_with(402), 384,
        )
        self.assertIs(out, original)
        self.assertEqual(0, added)

    def test_existing_debt_is_subtracted_exactly(self):
        state = self.state({402: {"STRAWBERRY": 8}})
        out, added, reservations = d4.advance_midgame_strawberry(
            action(), View(stock=5), state, tape_with(402, qty=10), 384,
        )
        self.assertEqual(2, added)
        self.assertEqual(((402, 2),), reservations)
        self.assertEqual(10, state.sale_window_debts[402]["STRAWBERRY"])
        self.assertEqual([["SELL", "STRAWBERRY", 2]], out["market"])

    def test_full_inherited_debt_map_is_validated_before_mutation(self):
        malformed = (
            {True: {"STRAWBERRY": 1}},
            {"402": {"STRAWBERRY": 1}},
            {720: {"STRAWBERRY": 1}},
            {402: []},
            {402: {"STRAWBERRY": True}},
            {402: {"STRAWBERRY": 1.0}},
            {402: {"STRAWBERRY": "1"}},
            {402: {"STRAWBERRY": -1}},
            {402: {"NOT_A_PRODUCT": 1}},
        )
        old_flush = base.EVENING_FLUSH
        base.EVENING_FLUSH = False
        try:
            for debts in malformed:
                with self.subTest(debts=debts):
                    original = action()
                    state = self.state(debts)
                    out, added, reservations = d4.advance_midgame_strawberry(
                        original, View(stock=5), state, tape_with(402, qty=10), 384,
                    )
                    self.assertIs(out, original)
                    self.assertEqual((0, ()), (added, reservations))
                    self.assertIs(state.sale_window_debts, debts)
        finally:
            base.EVENING_FLUSH = old_flush

    def test_order_cap_and_future_pickup_block(self):
        original = action([["SELL", "WHEAT", 1] for _ in range(base.MAX_ORDERS)])
        state = self.state()
        out, added, _ = d4.advance_midgame_strawberry(
            original, View(), state, tape_with(402), 384,
        )
        self.assertIs(out, original)
        self.assertEqual(0, added)

        original = action()
        state = self.state()
        out, added, _ = d4.advance_midgame_strawberry(
            original, View(), state, tape_with(402, pickup_step=398), 384,
        )
        self.assertIs(out, original)
        self.assertEqual(0, added)


if __name__ == "__main__":
    unittest.main()
