# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import unittest

from multi_lot_portfolio import PortfolioError, select_portfolio


def candidate(item, quantity, gain, *, forced=False, future=0):
    plan = [(10, quantity)]
    if future:
        plan.append((11, future))
    return {
        "item": item,
        "plan": tuple(plan),
        "info": {"item": item},
        "rank": (forced, gain),
    }


class PortfolioContracts(unittest.TestCase):
    def select(self, candidates, *, anchor, current, market=(), max_orders=10):
        return select_portfolio(
            candidates=candidates,
            anchor_item=anchor,
            current=current,
            market=list(market),
            now=10,
            max_orders=max_orders,
        )

    def test_two_profitable_products_apply_when_slots_exist(self):
        rows = [candidate("MILK", 4, 9), candidate("EGG", 3, 5)]
        decision = self.select(rows, anchor="MILK", current={"MILK": 2, "EGG": 1})
        self.assertEqual([row["item"] for row in decision.selected], ["MILK", "EGG"])
        self.assertEqual(decision.suffix_slots_used, 2)

    def test_one_free_slot_keeps_anchor_and_rejects_extra_claimant(self):
        rows = [candidate("MILK", 4, 2), candidate("EGG", 3, 99)]
        market = [["BUY_SEED", "CORN", 1]] * 8 + [["PASS"]]
        decision = self.select(
            rows, anchor="MILK", current={"MILK": 2, "EGG": 1},
            market=market, max_orders=10,
        )
        self.assertEqual([row["item"] for row in decision.selected], ["MILK"])
        self.assertEqual(decision.skipped_slots, ("EGG",))

    def test_stronger_extra_claimant_wins_only_remaining_slot(self):
        rows = [
            candidate("MILK", 2, 100),
            candidate("EGG", 3, 4),
            candidate("WOOL", 5, 8),
        ]
        market = [["SELL", "MILK", 2]] + [["PASS"]] * 8
        decision = self.select(
            rows, anchor="MILK", current={"MILK": 2, "EGG": 1, "WOOL": 1},
            market=market, max_orders=10,
        )
        self.assertEqual([row["item"] for row in decision.selected], ["MILK", "WOOL"])
        self.assertEqual(decision.skipped_slots, ("EGG",))

    def test_inherited_sell_rows_do_not_consume_suffix_slots(self):
        rows = [candidate("MILK", 4, 9), candidate("EGG", 2, 5)]
        market = [["SELL", "MILK", 4], ["SELL", "EGG", 2]] + [["PASS"]] * 8
        decision = self.select(
            rows, anchor="MILK", current={"MILK": 4, "EGG": 2},
            market=market, max_orders=10,
        )
        self.assertEqual([row["item"] for row in decision.selected], ["MILK", "EGG"])
        self.assertEqual(decision.suffix_slots_used, 0)

    def test_extra_current_decrease_is_excluded_but_anchor_is_preserved(self):
        rows = [candidate("MILK", 1, 9), candidate("EGG", 1, 8)]
        decision = self.select(
            rows, anchor="MILK", current={"MILK": 4, "EGG": 3}, max_orders=10,
        )
        self.assertEqual([row["item"] for row in decision.selected], ["MILK"])
        self.assertEqual(decision.skipped_decrease, ("EGG",))

    def test_forced_feasibility_rank_precedes_gain_for_scarce_slot(self):
        rows = [
            candidate("MILK", 2, 1),
            candidate("EGG", 2, 500),
            candidate("WOOL", 2, -2, forced=True),
        ]
        market = [["SELL", "MILK", 2]] + [["PASS"]] * 8
        decision = self.select(
            rows, anchor="MILK", current={"MILK": 2, "EGG": 1, "WOOL": 1},
            market=market, max_orders=10,
        )
        self.assertEqual([row["item"] for row in decision.selected], ["MILK", "WOOL"])

    def test_duplicate_candidate_fails_closed(self):
        with self.assertRaises(PortfolioError):
            self.select(
                [candidate("MILK", 2, 1), candidate("MILK", 3, 2)],
                anchor="MILK", current={"MILK": 1},
            )

    def test_malformed_sell_quantity_fails_closed(self):
        with self.assertRaises(PortfolioError):
            self.select(
                [candidate("MILK", 2, 1)], anchor="MILK", current={"MILK": 1},
                market=[["SELL", "MILK", "2"]],
            )

    def test_nonfinite_rank_fails_closed(self):
        with self.assertRaises(PortfolioError):
            self.select(
                [candidate("MILK", 2, float("nan"))],
                anchor="MILK", current={"MILK": 1},
            )

    def test_exact_rank_tie_retains_evaluation_order(self):
        rows = [
            candidate("MILK", 2, 10),
            candidate("EGG", 2, 5),
            candidate("WOOL", 2, 5),
        ]
        market = [["SELL", "MILK", 2]] + [["PASS"]] * 8
        decision = self.select(
            rows, anchor="MILK", current={"MILK": 2, "EGG": 1, "WOOL": 1},
            market=market, max_orders=10,
        )
        self.assertEqual([row["item"] for row in decision.selected], ["MILK", "EGG"])
        self.assertEqual(decision.skipped_slots, ("WOOL",))


if __name__ == "__main__":
    unittest.main()
