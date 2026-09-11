import importlib.util
import pathlib
import sys
import unittest
from types import SimpleNamespace

HERE = pathlib.Path(__file__).resolve().parent
OVERLAY = HERE.parents[1] / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))
spec = importlib.util.spec_from_file_location("d4_candidate", HERE / "candidate.py")
d4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d4)
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


class D4Tests(unittest.TestCase):
    def state(self, debts=None):
        return SimpleNamespace(queues={}, sale_window_debts=dict(debts or {}))

    def test_advances_only_beyond_parent_horizon_same_day(self):
        old = base.SALE_HORIZON
        base.SALE_HORIZON = 8
        try:
            original = action()
            state = self.state()
            out, added, reservations = d4.advance_midgame_strawberry(
                original, View(stock=12, price=200), state, tape_with(402), 384,
                min_price=180,
            )
            self.assertEqual(12, added)
            self.assertEqual(((402, 12),), reservations)
            self.assertEqual([["SELL", "STRAWBERRY", 12]], out["market"])
            self.assertEqual({"STRAWBERRY": 12}, state.sale_window_debts[402])
            self.assertIsNot(out, original)
        finally:
            base.SALE_HORIZON = old

    def test_parent_horizon_remains_parent_owned(self):
        original = action()
        state = self.state()
        out, added, reservations = d4.advance_midgame_strawberry(
            original, View(), state, tape_with(390), 384, min_price=180,
        )
        self.assertIs(out, original)
        self.assertEqual((0, ()), (added, reservations))
        self.assertEqual({}, state.sale_window_debts)

    def test_price_threshold_is_fail_closed_and_identity(self):
        original = action()
        state = self.state()
        out, added, _ = d4.advance_midgame_strawberry(
            original, View(price=179), state, tape_with(402), 384, min_price=180,
        )
        self.assertIs(out, original)
        self.assertEqual(0, added)
        self.assertEqual({}, state.sale_window_debts)

    def test_current_strawberry_sell_is_h4_owned(self):
        original = action([["SELL", "STRAWBERRY", 2]])
        state = self.state()
        out, added, _ = d4.advance_midgame_strawberry(
            original, View(), state, tape_with(402), 384, min_price=180,
        )
        self.assertIs(out, original)
        self.assertEqual(0, added)

    def test_future_pickup_blocks_before_due(self):
        original = action()
        state = self.state()
        out, added, _ = d4.advance_midgame_strawberry(
            original, View(), state, tape_with(402, pickup_step=398), 384,
            min_price=180,
        )
        self.assertIs(out, original)
        self.assertEqual(0, added)

    def test_existing_debt_is_subtracted_exactly(self):
        original = action()
        state = self.state({402: {"STRAWBERRY": 8}})
        out, added, reservations = d4.advance_midgame_strawberry(
            original, View(stock=5), state, tape_with(402, qty=10), 384,
            min_price=180,
        )
        self.assertEqual(2, added)
        self.assertEqual(((402, 2),), reservations)
        self.assertEqual(10, state.sale_window_debts[402]["STRAWBERRY"])
        self.assertEqual([["SELL", "STRAWBERRY", 2]], out["market"])

    def test_never_crosses_midnight(self):
        original = action()
        state = self.state()
        out, added, _ = d4.advance_midgame_strawberry(
            original, View(), state, tape_with(385), 383, min_price=180,
        )
        self.assertIs(out, original)
        self.assertEqual(0, added)

    def test_order_cap_blocks_without_mutation(self):
        original = action([["SELL", "WHEAT", 1] for _ in range(base.MAX_ORDERS)])
        state = self.state()
        out, added, _ = d4.advance_midgame_strawberry(
            original, View(), state, tape_with(402), 384, min_price=180,
        )
        self.assertIs(out, original)
        self.assertEqual(0, added)

    def test_outside_midgame_is_identity(self):
        for step in (287, 456):
            original = action()
            state = self.state()
            out, added, _ = d4.advance_midgame_strawberry(
                original, View(), state, tape_with(min(step + 20, base.LAST_STEP)), step,
                min_price=180,
            )
            self.assertIs(out, original)
            self.assertEqual(0, added)

    def test_bad_threshold_types_rejected_by_install(self):
        for value in (True, 1, 2.5, "180"):
            with self.assertRaises(ValueError):
                d4.install(d4_min_price=value)
        self.assertIs(d4.install(d4_min_price=None), d4.d4_agent)


if __name__ == "__main__":
    unittest.main()
