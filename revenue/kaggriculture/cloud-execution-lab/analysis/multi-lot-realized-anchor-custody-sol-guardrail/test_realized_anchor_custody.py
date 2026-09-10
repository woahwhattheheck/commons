# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import hashlib
import math
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
PREDECESSOR = LAB / "candidates" / "multi-lot-portfolio-sol-pro"
if str(PREDECESSOR) not in sys.path:
    sys.path.insert(0, str(PREDECESSOR))

from realized_anchor_custody import (
    CustodyError,
    render_suffix,
    select_with_realized_anchor_custody,
)


def candidate(item: str, quantity: int, gain: float, *, forced: bool = False, now: int = 10):
    return {
        "item": item,
        "plan": ((now, quantity),),
        "info": {"witness": item},
        "rank": (forced, gain),
    }


class RealizedAnchorCustodyTests(unittest.TestCase):
    def setUp(self):
        self.market = [["PASS"] for _ in range(8)]

    def test_exact_predecessor_source_binding(self):
        source = PREDECESSOR / "multi_lot_portfolio.py"
        payload = source.read_bytes()
        git_blob = hashlib.sha1(
            f"blob {len(payload)}\0".encode("ascii") + payload
        ).hexdigest()
        self.assertEqual(git_blob, "b7478242f19ef8554bb4e5b102fe1f9b61811a26")
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "87e9e14981a4c9ecf6b98bd1eb0b76d5599ff41a2c80bf320e84b3b90d503d89",
        )

    def test_predecessor_claims_anchor_but_renderer_drops_it(self):
        """Exact predecessor killer for the rejected allocator's blind spot."""
        from multi_lot_portfolio import select_portfolio

        current = {"EGG": 1, "MILK": 0, "WOOL": 0}
        rows = [candidate("MILK", 1, 10), candidate("WOOL", 1, 20)]
        old = select_portfolio(
            candidates=rows,
            anchor_item="WOOL",
            current=current,
            market=self.market,
            now=10,
            max_orders=10,
        )
        old_quantities = dict(current)
        for row in old.selected:
            old_quantities[row["item"]] = dict(row["plan"])[10]
        available = {"EGG": 1, "MILK": 1, "WOOL": 1}
        old_suffix = render_suffix(
            quantities=old_quantities,
            offered={},
            available=available,
            free_slots=2,
        )
        scalar_suffix = render_suffix(
            quantities={**current, "WOOL": 1},
            offered={},
            available=available,
            free_slots=2,
        )
        self.assertEqual([row["item"] for row in old.selected], ["MILK", "WOOL"])
        self.assertEqual(old.suffix_slots_used, 2)
        self.assertEqual(scalar_suffix, (("EGG", 1), ("WOOL", 1)))
        self.assertEqual(old_suffix, (("EGG", 1), ("MILK", 1)))
        self.assertNotIn(("WOOL", 1), old_suffix)

    def test_repair_rejects_extra_that_displaces_anchor(self):
        current = {"EGG": 1, "MILK": 0, "WOOL": 0}
        decision = select_with_realized_anchor_custody(
            candidates=[candidate("MILK", 1, 10), candidate("WOOL", 1, 20)],
            anchor_item="WOOL",
            current=current,
            available={"EGG": 1, "MILK": 1, "WOOL": 1},
            market=self.market,
            now=10,
            max_orders=10,
        )
        self.assertEqual([row["item"] for row in decision.selected], ["WOOL"])
        self.assertEqual(decision.rejected_unrealized, ("MILK",))
        self.assertEqual(decision.scalar_suffix, (("EGG", 1), ("WOOL", 1)))
        self.assertEqual(decision.portfolio_suffix, decision.scalar_suffix)

    def test_extra_after_anchor_fits_without_displacement(self):
        current = {"EGG": 0, "MILK": 0, "WOOL": 0, "YAM": 0}
        available = {"EGG": 0, "MILK": 0, "WOOL": 1, "YAM": 1}
        decision = select_with_realized_anchor_custody(
            candidates=[candidate("YAM", 1, 10), candidate("WOOL", 1, 20)],
            anchor_item="WOOL",
            current=current,
            available=available,
            market=self.market,
            now=10,
            max_orders=10,
        )
        self.assertEqual([row["item"] for row in decision.selected], ["YAM", "WOOL"])
        self.assertEqual(decision.portfolio_suffix, (("WOOL", 1), ("YAM", 1)))

    def test_existing_offer_needs_no_suffix_and_preserves_anchor(self):
        market = [["PASS"] for _ in range(8)] + [["SELL", "MILK", 3]]
        current = {"MILK": 0, "WOOL": 0}
        available = {"MILK": 2, "WOOL": 1}
        decision = select_with_realized_anchor_custody(
            candidates=[candidate("MILK", 2, 10), candidate("WOOL", 1, 20)],
            anchor_item="WOOL",
            current=current,
            available=available,
            market=market,
            now=10,
            max_orders=10,
        )
        self.assertEqual([row["item"] for row in decision.selected], ["MILK", "WOOL"])
        self.assertEqual(decision.portfolio_suffix, (("WOOL", 1),))

    def test_decreasing_extra_is_rejected(self):
        current = {"MILK": 2, "WOOL": 0}
        available = {"MILK": 2, "WOOL": 1}
        decision = select_with_realized_anchor_custody(
            candidates=[candidate("MILK", 1, 100), candidate("WOOL", 1, 1)],
            anchor_item="WOOL",
            current=current,
            available=available,
            market=self.market,
            now=10,
            max_orders=10,
        )
        self.assertEqual([row["item"] for row in decision.selected], ["WOOL"])
        self.assertEqual(decision.rejected_decrease, ("MILK",))

    def test_forced_rank_precedes_gain_for_single_remaining_slot(self):
        market = [["PASS"] for _ in range(8)]
        current = {"MILK": 0, "PORK": 0, "WOOL": 0}
        decision = select_with_realized_anchor_custody(
            candidates=[
                candidate("WOOL", 1, 100),
                candidate("PORK", 1, -1, forced=True),
                candidate("MILK", 1, 200),
            ],
            anchor_item="MILK",
            current=current,
            available={key: 1 for key in current},
            market=market,
            now=10,
            max_orders=10,
        )
        self.assertEqual([row["item"] for row in decision.selected], ["PORK", "MILK"])
        self.assertEqual(decision.portfolio_suffix, (("MILK", 1), ("PORK", 1)))
        self.assertEqual(decision.rejected_unrealized, ("WOOL",))

    def test_exact_rank_tie_retains_input_order(self):
        market = [["PASS"] for _ in range(8)]
        current = {"MILK": 0, "PORK": 0, "WOOL": 0}
        decision = select_with_realized_anchor_custody(
            candidates=[
                candidate("PORK", 1, 10),
                candidate("WOOL", 1, 10),
                candidate("MILK", 1, 20),
            ],
            anchor_item="MILK",
            current=current,
            available={key: 1 for key in current},
            market=market,
            now=10,
            max_orders=10,
        )
        self.assertEqual([row["item"] for row in decision.selected], ["PORK", "MILK"])
        self.assertEqual(decision.rejected_unrealized, ("WOOL",))

    def test_extra_cannot_drop_nonanchor_scalar_suffix_row(self):
        # Anchor EGG remains realized, but PORK would evict scalar WOOL.  Full
        # scalar custody rejects it; anchor-only checking would admit it.
        market = [["PASS"] for _ in range(7)]
        current = {"EGG": 0, "MILK": 1, "PORK": 0, "WOOL": 1}
        decision = select_with_realized_anchor_custody(
            candidates=[candidate("PORK", 1, 100), candidate("EGG", 1, 1)],
            anchor_item="EGG",
            current=current,
            available={key: 1 for key in current},
            market=market,
            now=10,
            max_orders=10,
        )
        self.assertEqual([row["item"] for row in decision.selected], ["EGG"])
        self.assertEqual(decision.scalar_suffix, (("EGG", 1), ("MILK", 1), ("WOOL", 1)))
        self.assertEqual(decision.portfolio_suffix, decision.scalar_suffix)
        self.assertEqual(decision.rejected_scalar_displacement, ("PORK",))

    def test_extra_cannot_shift_scalar_suffix_indices_even_with_spare_slot(self):
        market = [["PASS"] for _ in range(6)]
        current = {"MILK": 0, "WOOL": 0}
        decision = select_with_realized_anchor_custody(
            candidates=[candidate("MILK", 1, 100), candidate("WOOL", 1, 1)],
            anchor_item="WOOL",
            current=current,
            available={key: 1 for key in current},
            market=market,
            now=10,
            max_orders=10,
        )
        self.assertEqual([row["item"] for row in decision.selected], ["WOOL"])
        self.assertEqual(decision.scalar_suffix, (("WOOL", 1),))
        self.assertEqual(decision.rejected_scalar_displacement, ("MILK",))

    def test_inputs_are_not_mutated(self):
        current = {"MILK": 0, "WOOL": 0}
        rows = [candidate("MILK", 1, 10), candidate("WOOL", 1, 20)]
        market = copy.deepcopy(self.market)
        available = {"MILK": 1, "WOOL": 1}
        before = copy.deepcopy((current, available, rows, market))
        select_with_realized_anchor_custody(
            candidates=rows,
            anchor_item="WOOL",
            current=current,
            available=available,
            market=market,
            now=10,
            max_orders=10,
        )
        self.assertEqual((current, available, rows, market), before)

    def test_scalar_anchor_unrealized_fails_closed(self):
        current = {"EGG": 1, "WOOL": 0}
        with self.assertRaisesRegex(CustodyError, "scalar anchor"):
            select_with_realized_anchor_custody(
                candidates=[candidate("WOOL", 1, 20)],
                anchor_item="WOOL",
                current=current,
                available={"EGG": 1, "WOOL": 1},
                market=[["PASS"] for _ in range(10)],
                now=10,
                max_orders=10,
            )

    def test_scalar_anchor_capacity_clip_fails_closed(self):
        with self.assertRaisesRegex(CustodyError, "scalar anchor"):
            select_with_realized_anchor_custody(
                candidates=[candidate("WOOL", 2, 20)],
                anchor_item="WOOL",
                current={"WOOL": 0},
                available={"WOOL": 1},
                market=[],
                now=10,
                max_orders=10,
            )

    def test_malformed_inputs_fail_closed(self):
        cases = [
            [candidate("WOOL", 1, math.inf)],
            [{**candidate("WOOL", 1, 1), "rank": (1, 1)}],
            [{**candidate("WOOL", 1, 1), "plan": ((9, 1),)}],
            [{**candidate("WOOL", 1, 1), "plan": ((10, True),)}],
        ]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(CustodyError):
                select_with_realized_anchor_custody(
                    candidates=rows,
                    anchor_item="WOOL",
                    current={"WOOL": 0},
                    available={"WOOL": 1},
                    market=[],
                    now=10,
                    max_orders=10,
                )

    def test_duplicate_item_and_alias_fail_closed(self):
        row = candidate("WOOL", 1, 1)
        with self.assertRaisesRegex(CustodyError, "duplicate"):
            select_with_realized_anchor_custody(
                candidates=[row, row],
                anchor_item="WOOL",
                current={"WOOL": 0},
                available={"WOOL": 1},
                market=[],
                now=10,
                max_orders=10,
            )


if __name__ == "__main__":
    unittest.main()
