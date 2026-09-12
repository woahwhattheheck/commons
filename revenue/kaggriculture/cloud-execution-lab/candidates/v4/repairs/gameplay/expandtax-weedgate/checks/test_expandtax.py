# SPDX-License-Identifier: Apache-2.0
"""Unit tests for R04-EXPANDTAX (expandtax.py). Pure-logic: no engine import."""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import expandtax
from expandtax import (TrailingBooks, filter_market_orders, next_unlock_price,
                       should_expand)


def _obs(day=10, quadrants=("NW",)):
    return {"day": day,
            "farm": {"unlocked_quadrants": list(quadrants), "money": 5000}}


def _cfg(on=True):
    return {"r04_expandtax": on, "turnsPerDay": 24, "episodeSteps": 722}


def _books(rev, act):
    b = TrailingBooks()
    b.note_day(3000.0, 20, 100)
    b.note_day(3000.0 + rev * 20, 20,
               100 + int(rev / max(act, 1e-9) * 20) if act else 100)
    return b


class TestShouldExpand(unittest.TestCase):
    def test_blocks_when_books_zero(self):
        # No revenue history -> gate blocks (fail-closed).
        self.assertFalse(should_expand(1000, 0.0, 5.0, 20))

    def test_allows_when_weed_tax_cleared(self):
        # E=50 $/tile/day, A=5, W=.013 -> tax=.065; amortized=2.
        self.assertTrue(should_expand(1000, 50.0, 5.0, 20))

    def test_blocks_on_high_price_short_horizon(self):
        # $4000 with 2 days left: amortized 80 $/tile/day kills it.
        self.assertFalse(should_expand(4000, 50.0, 5.0, 2))

    def test_malformed_fails_closed(self):
        self.assertFalse(should_expand(None, 1.0, 1.0, 5))
        self.assertFalse(should_expand(1000, "x", 1.0, 5))
        self.assertFalse(should_expand(1000, 1.0, 1.0, 0))
        self.assertFalse(should_expand(-1000, 1.0, 1.0, 5))

    def test_negative_action_value_clamped(self):
        # Negative $/action can't make weed tax negative (no perverse incentive).
        self.assertFalse(should_expand(1000, 0.05, -100.0, 20))


class TestFilter(unittest.TestCase):
    def test_off_flag_returns_identical_object(self):
        action = {"farmer": ["PASS"], "hands": [],
                  "market": [["BUY_LAND"], ["SELL", "CARROT", 3],
                             ["BUY_LAND"]]}
        out = filter_market_orders(action, _obs(), {"r04_expandtax": False}, None)
        self.assertIs(out, action)

    def test_absent_flag_returns_identical_object(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["BUY_LAND"]]}
        out = filter_market_orders(action, _obs(), {}, None)
        self.assertIs(out, action)

    def test_truthy_nonbool_flag_returns_identical_object(self):
        action = {"farmer": ["PASS"], "hands": [],
                  "market": [["BUY_LAND"], ["BUY_LAND"]]}
        for poison in (1, "true", [True], {"enabled": True}):
            with self.subTest(poison=poison):
                self.assertIs(filter_market_orders(action, _obs(),
                                                   _cfg(poison), None), action)

    def test_no_buy_land_returns_identical_object(self):
        action = {"farmer": ["PASS"], "hands": [],
                  "market": [["SELL", "CARROT", 3]]}
        out = filter_market_orders(action, _obs(), _cfg(), _books(50, 5))
        self.assertIs(out, action)

    def test_gate_reject_strips_buy_land(self):
        action = {"farmer": ["PASS"], "hands": [],
                  "market": [["BUY_LAND"], ["SELL", "CARROT", 3]]}
        out = filter_market_orders(action, _obs(day=28), _cfg(), _books(1.0, 5))
        self.assertEqual(out["market"], [["SELL", "CARROT", 3]])

    def test_gate_reject_strips_every_land_and_preserves_other_rows(self):
        action = {"farmer": ["PASS"], "hands": [],
                  "market": [["BUY_LAND"], ["SELL", "CARROT", 3],
                             ["BUY_LAND"], ["HIRE"], ["BUY_LAND"]]}
        out = filter_market_orders(action, _obs(day=28), _cfg(), _books(1.0, 5))
        self.assertEqual(out["market"],
                         [["SELL", "CARROT", 3], ["HIRE"]])

    def test_gate_allow_keeps_single_land_action_identity(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["BUY_LAND"]]}
        out = filter_market_orders(action, _obs(day=5), _cfg(), _books(60, 5))
        self.assertIs(out, action)

    def test_first_1000_pass_second_2000_fail_keeps_only_first_land(self):
        # day10 => D=20. With E=3 and A=1: $1k threshold ~2.013 passes,
        # $2k threshold ~4.013 fails. The pre-callback verdict may authorize
        # only the first sequential BUY_LAND; unrelated rows retain order.
        self.assertTrue(should_expand(1000, 3.0, 1.0, 20))
        self.assertFalse(should_expand(2000, 3.0, 1.0, 20))
        action = {"farmer": ["PASS"], "hands": [],
                  "market": [["BUY_LAND"], ["SELL", "CARROT", 3],
                             ["BUY_LAND"], ["HIRE"]]}
        out = filter_market_orders(action, _obs(day=10), _cfg(), _books(3.0, 1.0))
        self.assertIsNot(out, action)
        self.assertEqual(out["market"],
                         [["BUY_LAND"], ["SELL", "CARROT", 3], ["HIRE"]])
        self.assertEqual(action["market"],
                         [["BUY_LAND"], ["SELL", "CARROT", 3],
                          ["BUY_LAND"], ["HIRE"]])

    def test_even_high_edge_never_authorizes_second_land_from_one_verdict(self):
        action = {"farmer": ["PASS"], "hands": [],
                  "market": [["BUY_LAND"], ["BUY_LAND"],
                             ["SELL", "CARROT", 3]]}
        out = filter_market_orders(action, _obs(day=5), _cfg(), _books(60, 5))
        self.assertEqual(out["market"],
                         [["BUY_LAND"], ["SELL", "CARROT", 3]])

    def test_all_unlocked_strips_every_noop_land_only(self):
        action = {"farmer": ["PASS"], "hands": [],
                  "market": [["SELL", "CARROT", 3], ["BUY_LAND"],
                             ["HIRE"], ["BUY_LAND"]]}
        out = filter_market_orders(
            action,
            _obs(quadrants=("NW", "NE", "SW", "SE")),
            _cfg(),
            _books(60, 5),
        )
        self.assertEqual(out["market"],
                         [["SELL", "CARROT", 3], ["HIRE"]])

    def test_malformed_action_fails_closed(self):
        self.assertIsNone(filter_market_orders(None, _obs(), _cfg(), None))
        self.assertEqual(filter_market_orders({}, _obs(), _cfg(), None), {})
        # non-dict action passes through untouched
        self.assertEqual(filter_market_orders("x", _obs(), _cfg(), None), "x")


class TestNextUnlockPrice(unittest.TestCase):
    def test_first_unlock_1000(self):
        self.assertEqual(next_unlock_price(_obs(quadrants=("NW",))), 1000)

    def test_second_unlock_2000(self):
        self.assertEqual(next_unlock_price(_obs(quadrants=("NW", "NE"))), 2000)

    def test_all_unlocked_none(self):
        self.assertIsNone(
            next_unlock_price(_obs(quadrants=("NW", "NE", "SW", "SE"))))

    def test_malformed_obs_fails_closed(self):
        self.assertEqual(next_unlock_price({}), 1000)  # default: NW only


class TestTrailingBooks(unittest.TestCase):
    def test_empty_books_zero(self):
        b = TrailingBooks()
        self.assertEqual(b.rev_per_tile_day, 0.0)
        self.assertEqual(b.dollars_per_action, 0.0)

    def test_single_day_zero(self):
        b = TrailingBooks()
        b.note_day(3000.0, 20, 100)
        self.assertEqual(b.rev_per_tile_day, 0.0)  # no delta yet

    def test_delta_math(self):
        b = TrailingBooks()
        b.note_day(3000.0, 20, 100)
        b.note_day(4000.0, 20, 200)   # +1000 over 20 tiles, 100 actions
        self.assertAlmostEqual(b.rev_per_tile_day, 50.0)
        self.assertAlmostEqual(b.dollars_per_action, 10.0)

    def test_window_bounded(self):
        b = TrailingBooks()
        for i in range(10):
            b.note_day(3000.0 + i * 100, 20, 100 + i)
        self.assertLessEqual(len(b._days), TrailingBooks.WINDOW + 1)


if __name__ == "__main__":
    unittest.main()
