# SPDX-License-Identifier: Apache-2.0
import copy
import unittest

from h4_current import (
    BoundaryError,
    DONOR_BLOB,
    DONOR_COMMIT,
    reconcile_strawberry_current,
)


def action(*, market=None, farmer=None, hands=None):
    return {
        "market": [] if market is None else market,
        "farmer": ["PASS"] if farmer is None else farmer,
        "hands": [] if hands is None else hands,
        "opaque": {"preserve": [1, 2, 3]},
    }


class H4CurrentABITest(unittest.TestCase):
    def call(self, selected, **overrides):
        kwargs = dict(
            enabled=True,
            step=200,
            advance_start=72,
            last_step=718,
            sale_horizon=8,
            projected_shed={"STRAWBERRY": 10, "WHEAT": 5},
            strawberry_price=4,
            future_actions={
                201: action(market=[["SELL", "STRAWBERRY", 3]]),
                202: action(market=[["SELL", "STRAWBERRY", 4]]),
                203: action(),
                204: action(),
                205: action(),
                206: action(),
                207: action(),
                208: action(),
            },
            sale_window_debts={201: {"STRAWBERRY": 1}},
            queued_commands=[],
            actor_inventories=[{}],
            animal_items={"COW", "SHEEP", "GOAT", "CHICKEN"},
        )
        kwargs.update(overrides)
        return reconcile_strawberry_current(selected, **kwargs)

    def test_provenance_is_exact_submitted_h4(self):
        self.assertEqual(
            DONOR_COMMIT,
            "a90d888f03987ef0b35cfd20ec3519c6144db08a",
        )
        self.assertEqual(
            DONOR_BLOB,
            "d6e3ffb76856ff171dab2a45b4d3c1788f2b2cb8",
        )

    def test_disabled_is_exact_identity_and_no_debt_copy(self):
        selected = action(market=[["SELL", "STRAWBERRY", 2], ["HIRE"]])
        debts = {201: {"STRAWBERRY": 1}}
        out, debt_out, receipt = self.call(
            selected, enabled=False, sale_window_debts=debts
        )
        self.assertIs(out, selected)
        self.assertIs(debt_out, debts)
        self.assertEqual(receipt["reason"], "disabled")

    def test_topup_only_enlarges_existing_row_and_updates_exact_debt(self):
        selected = action(
            market=[
                ["SELL", "STRAWBERRY", 2],
                ["HIRE"],
                ["SELL", "WHEAT", 1],
            ]
        )
        original = copy.deepcopy(selected)
        debts = {201: {"STRAWBERRY": 1}, 205: {"WHEAT": 9}}
        out, debt_out, receipt = self.call(
            selected,
            sale_window_debts=debts,
        )
        self.assertEqual(
            out["market"],
            [
                ["SELL", "STRAWBERRY", 8],
                ["HIRE"],
                ["SELL", "WHEAT", 1],
            ],
        )
        self.assertEqual(out["opaque"], selected["opaque"])
        self.assertEqual(receipt["reservations"], ((201, 2), (202, 4)))
        self.assertEqual(receipt["added_quantity"], 6)
        self.assertEqual(debt_out[201]["STRAWBERRY"], 3)
        self.assertEqual(debt_out[202]["STRAWBERRY"], 4)
        self.assertEqual(debt_out[205]["WHEAT"], 9)
        self.assertEqual(selected, original)
        self.assertEqual(debts, {201: {"STRAWBERRY": 1}, 205: {"WHEAT": 9}})

    def test_never_creates_a_missing_strawberry_sell(self):
        selected = action(market=[["SELL", "WHEAT", 2], ["HIRE"]])
        out, debts, receipt = self.call(selected)
        self.assertIs(out, selected)
        self.assertEqual(receipt["reason"], "requires-one-current-sell")
        self.assertEqual(debts, {201: {"STRAWBERRY": 1}})

    def test_requires_exactly_one_current_strawberry_sell(self):
        selected = action(
            market=[
                ["SELL", "STRAWBERRY", 1],
                ["SELL", "STRAWBERRY", 1],
            ]
        )
        out, _, receipt = self.call(selected)
        self.assertIs(out, selected)
        self.assertEqual(receipt["reason"], "requires-one-current-sell")

    def test_current_buy_product_blocks(self):
        selected = action(
            market=[
                ["SELL", "STRAWBERRY", 2],
                ["BUY_PRODUCT", "STRAWBERRY", 1],
            ]
        )
        out, _, receipt = self.call(selected)
        self.assertIs(out, selected)
        self.assertEqual(receipt["reason"], "current-buy-product")

    def test_price_floor_blocks(self):
        selected = action(market=[["SELL", "STRAWBERRY", 2]])
        out, _, receipt = self.call(selected, strawberry_price=1)
        self.assertIs(out, selected)
        self.assertEqual(receipt["reason"], "price-floor")

    def test_current_or_queued_pickup_blocks(self):
        selected = action(
            market=[["SELL", "STRAWBERRY", 2]],
            farmer=["PICKUP", "STRAWBERRY", 1],
        )
        out, _, receipt = self.call(selected)
        self.assertEqual(receipt["reason"], "current-pickup")
        self.assertIs(out, selected)

        selected = action(market=[["SELL", "STRAWBERRY", 2]])
        out, _, receipt = self.call(
            selected, queued_commands=[["PICKUP", "STRAWBERRY", 1]]
        )
        self.assertEqual(receipt["reason"], "queued-pickup")
        self.assertIs(out, selected)

    def test_animal_place_fallback_blocks_only_if_actor_owns_animal(self):
        selected = action(
            market=[["SELL", "STRAWBERRY", 2]],
            farmer=["PLACE", "COW", 1, 2],
        )
        out, _, receipt = self.call(
            selected,
            actor_inventories=[{"COW": 1}],
        )
        self.assertEqual(receipt["reason"], "animal-place-fallback")
        self.assertIs(out, selected)

        out, _, receipt = self.call(
            selected,
            actor_inventories=[{"COW": 0}],
        )
        self.assertTrue(receipt["applied"])

    def test_future_pickup_is_a_boundary_but_keeps_earlier_backing(self):
        selected = action(market=[["SELL", "STRAWBERRY", 2]])
        futures = {
            201: action(market=[["SELL", "STRAWBERRY", 2]]),
            202: action(
                market=[["SELL", "STRAWBERRY", 8]],
                farmer=["PICKUP", "STRAWBERRY", 1],
            ),
            **{s: action() for s in range(203, 209)},
        }
        out, debts, receipt = self.call(
            selected,
            future_actions=futures,
            sale_window_debts={},
        )
        self.assertEqual(out["market"][0][2], 4)
        self.assertEqual(receipt["reservations"], ((201, 2),))
        self.assertEqual(debts, {201: {"STRAWBERRY": 2}})

    def test_future_buy_product_is_a_boundary_but_keeps_earlier_backing(self):
        selected = action(market=[["SELL", "STRAWBERRY", 2]])
        futures = {
            201: action(market=[["SELL", "STRAWBERRY", 1]]),
            202: action(
                market=[
                    ["BUY_PRODUCT", "STRAWBERRY", 1],
                    ["SELL", "STRAWBERRY", 8],
                ]
            ),
            **{s: action() for s in range(203, 209)},
        }
        out, _, receipt = self.call(
            selected,
            future_actions=futures,
            sale_window_debts={},
        )
        self.assertEqual(out["market"][0][2], 3)
        self.assertEqual(receipt["reservations"], ((201, 1),))

    def test_projected_stock_is_hard_cap(self):
        selected = action(market=[["SELL", "STRAWBERRY", 2]])
        out, debts, receipt = self.call(
            selected,
            projected_shed={"STRAWBERRY": 5},
            sale_window_debts={},
        )
        self.assertEqual(out["market"][0][2], 5)
        self.assertEqual(receipt["added_quantity"], 3)
        self.assertEqual(sum(v["STRAWBERRY"] for v in debts.values()), 3)

    def test_existing_debt_prevents_double_advance(self):
        selected = action(market=[["SELL", "STRAWBERRY", 2]])
        out, debts, receipt = self.call(
            selected,
            sale_window_debts={
                201: {"STRAWBERRY": 3},
                202: {"STRAWBERRY": 4},
            },
        )
        self.assertIs(out, selected)
        self.assertEqual(
            debts,
            {201: {"STRAWBERRY": 3}, 202: {"STRAWBERRY": 4}},
        )
        self.assertEqual(receipt["reason"], "no-backed-future-sale")

    def test_before_step_144_horizon_is_exactly_one(self):
        selected = action(market=[["SELL", "STRAWBERRY", 2]])
        futures = {
            101: action(market=[["SELL", "STRAWBERRY", 1]]),
        }
        out, debts, receipt = self.call(
            selected,
            step=100,
            future_actions=futures,
            sale_window_debts={},
        )
        self.assertEqual(out["market"][0][2], 3)
        self.assertEqual(receipt["window_end"], 101)
        self.assertEqual(debts, {101: {"STRAWBERRY": 1}})

    def test_day_boundary_is_not_crossed(self):
        selected = action(market=[["SELL", "STRAWBERRY", 2]])
        out, _, receipt = self.call(
            selected,
            step=215,
            future_actions={},
            sale_window_debts={},
        )
        self.assertIs(out, selected)
        self.assertEqual(receipt["reason"], "empty-future-window")

    def test_incomplete_authenticated_future_window_fails_closed(self):
        selected = action(market=[["SELL", "STRAWBERRY", 2]])
        futures = {201: action(market=[["SELL", "STRAWBERRY", 3]])}
        out, debts, receipt = self.call(
            selected,
            future_actions=futures,
            sale_window_debts={},
        )
        self.assertIs(out, selected)
        self.assertEqual(debts, {})
        self.assertEqual(receipt["reason"], "incomplete-future-window")
        self.assertEqual(receipt["missing_due_step"], 202)

    def test_malformed_future_sell_fails_closed(self):
        selected = action(market=[["SELL", "STRAWBERRY", 2]])
        futures = {
            201: action(market=[["SELL", "STRAWBERRY", "x"]]),
            **{s: action() for s in range(202, 209)},
        }
        out, _, receipt = self.call(
            selected,
            future_actions=futures,
            sale_window_debts={},
        )
        self.assertIs(out, selected)
        self.assertEqual(receipt["reason"], "malformed-future-sell")

    def test_strict_enabled_bool_and_boundary_cardinality(self):
        selected = action(market=[["SELL", "STRAWBERRY", 2]])
        with self.assertRaises(TypeError):
            self.call(selected, enabled=1)
        with self.assertRaises(BoundaryError):
            self.call(selected, actor_inventories=[])

    def test_terminal_and_pre_advance_steps_are_identity(self):
        selected = action(market=[["SELL", "STRAWBERRY", 2]])
        out, _, receipt = self.call(selected, step=718, future_actions={})
        self.assertIs(out, selected)
        self.assertEqual(receipt["reason"], "outside-window")
        out, _, receipt = self.call(selected, step=71, future_actions={})
        self.assertIs(out, selected)
        self.assertEqual(receipt["reason"], "outside-window")


if __name__ == "__main__":
    unittest.main()
