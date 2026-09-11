from __future__ import annotations

import copy
import unittest

import candidate as c5


def obs(step: int, inventory: int, *, price: int = 25, shops=None, player: int = 0):
    return {
        "step": step,
        "player": player,
        "market": {
            "inventory": {"WHEAT": inventory},
            "prices": {"WHEAT": price},
        },
        "town": {"unlocked_shops": list(shops or [])},
    }


def action(*rows):
    return {"farmer": ["PASS"], "hands": [], "market": [list(row) for row in rows]}


class WheatDemandRiderTests(unittest.TestCase):
    def test_rival_demand_lower_bound_exact_without_own_buy_or_town(self):
        self.assertEqual(c5._rival_wheat_demand_lower_bound(100, 97, 0, 0), 3)

    def test_town_and_own_buy_cannot_fabricate_rival_demand(self):
        # Three units disappeared: one deterministic town unit + two units we
        # ourselves could have bought.  Rival lower bound is therefore zero.
        self.assertEqual(c5._rival_wheat_demand_lower_bound(100, 97, 1, 2), 0)

    def test_own_sell_only_makes_lower_bound_more_conservative(self):
        # Example realization: our SELL +3 and rival BUY -5 produce net -2.
        # The bound sees only -2 and proves at least two rival net-buy units.
        self.assertEqual(c5._rival_wheat_demand_lower_bound(100, 98, 0, 0), 2)

    def test_town_consumption_matches_official_intervals(self):
        self.assertEqual(c5._town_wheat_consumption(obs(1, 100, shops=["BAKERY"])), 0)
        self.assertEqual(c5._town_wheat_consumption(obs(4, 100, shops=["BAKERY"])), 1)
        self.assertEqual(
            c5._town_wheat_consumption(obs(24, 100, shops=["BAKERY", "PIZZA_SHOP"])),
            3,
        )

    def test_unknown_town_shop_fails_closed(self):
        rider = c5.WheatDemandRider(enabled=True)
        parent = action(("SELL", "WHEAT", 2))
        self.assertIs(rider.apply(obs(4, 100, shops=["UNKNOWN"]), parent), parent)
        self.assertEqual(rider.players, {})

    def test_confirmed_demand_moves_only_wheat_row_to_new_trailing_slot(self):
        rider = c5.WheatDemandRider(enabled=True)
        first = action(("SELL", "MILK", 1))
        self.assertIs(rider.apply(obs(1, 100), first), first)

        parent = action(("SELL", "WHEAT", 3), ("SELL", "MILK", 2), ("SELL", "WOOL", 1))
        original = copy.deepcopy(parent)
        result = rider.apply(obs(2, 99, price=30), parent)

        self.assertIsNot(result, parent)
        self.assertEqual(parent, original)  # parent object is never mutated
        self.assertEqual(result["market"][0], [])
        self.assertEqual(result["market"][1], ["SELL", "MILK", 2])
        self.assertEqual(result["market"][2], ["SELL", "WOOL", 1])
        self.assertEqual(result["market"][3], ["SELL", "WHEAT", 3])
        self.assertEqual(rider.telemetry["relocations"], 1)
        self.assertEqual(rider.telemetry["moved_units"], 3)

    def test_disabled_arm_is_exact_parent_identity(self):
        rider = c5.WheatDemandRider(enabled=False)
        rider.apply(obs(1, 100), action())
        parent = action(("SELL", "WHEAT", 3), ("SELL", "MILK", 2))
        result = rider.apply(obs(2, 99, price=30), parent)
        self.assertIs(result, parent)
        self.assertEqual(rider.telemetry["confirmed_demand_transitions"], 1)
        self.assertEqual(rider.telemetry["relocations"], 0)

    def test_deterministic_town_tick_is_subtracted_before_authorization(self):
        rider = c5.WheatDemandRider(enabled=True)
        # Step 4 will consume one WHEAT at BAKERY after its market phase.
        rider.apply(obs(4, 100, shops=["BAKERY"]), action())
        parent = action(("SELL", "WHEAT", 3))
        result = rider.apply(obs(5, 99, price=30, shops=["BAKERY"]), parent)
        self.assertIs(result, parent)
        self.assertEqual(rider.telemetry["confirmed_demand_transitions"], 0)

    def test_own_buy_request_upper_bound_masks_possible_self_caused_drop(self):
        rider = c5.WheatDemandRider(enabled=True)
        rider.apply(obs(1, 100), action(("BUY_PRODUCT", "WHEAT", 2)))
        parent = action(("SELL", "WHEAT", 3))
        result = rider.apply(obs(2, 98, price=30), parent)
        self.assertIs(result, parent)
        self.assertEqual(rider.telemetry["confirmed_demand_transitions"], 0)

    def test_gap_or_rewind_does_not_authorize_on_stale_transition(self):
        rider = c5.WheatDemandRider(enabled=True)
        rider.apply(obs(1, 100), action())
        parent = action(("SELL", "WHEAT", 3))
        self.assertIs(rider.apply(obs(3, 90, price=30), parent), parent)
        self.assertEqual(rider.telemetry["relocations"], 0)

    def test_full_market_prefix_preserves_parent(self):
        rider = c5.WheatDemandRider(enabled=True)
        rider.apply(obs(1, 100), action())
        rows = [["SELL", "WHEAT", 1]] + [["SELL", "MILK", 1] for _ in range(9)]
        parent = {"farmer": ["PASS"], "hands": [], "market": rows}
        self.assertIs(rider.apply(obs(2, 99, price=30), parent), parent)

    def test_later_purchase_veto_preserves_sale_funding_order(self):
        rider = c5.WheatDemandRider(enabled=True)
        rider.apply(obs(1, 100), action())
        parent = action(("SELL", "WHEAT", 3), ("HIRE",), ("SELL", "MILK", 1))
        self.assertIs(rider.apply(obs(2, 99, price=30), parent), parent)

    def test_same_product_market_ambiguity_preserves_parent(self):
        rider = c5.WheatDemandRider(enabled=True)
        rider.apply(obs(1, 100), action())
        parent = action(("SELL", "WHEAT", 3), ("BUY_PRODUCT", "WHEAT", 1))
        self.assertIs(rider.apply(obs(2, 99, price=30), parent), parent)

    def test_floor_price_preserves_parent(self):
        rider = c5.WheatDemandRider(enabled=True)
        rider.apply(obs(1, 100), action())
        parent = action(("SELL", "WHEAT", 3))
        self.assertIs(rider.apply(obs(2, 99, price=1), parent), parent)

    def test_bool_quantity_does_not_authorize_mutation(self):
        rider = c5.WheatDemandRider(enabled=True)
        parent = action(("BUY_PRODUCT", "WHEAT", True))
        self.assertIs(rider.apply(obs(1, 100), parent), parent)
        self.assertEqual(rider.players, {})


if __name__ == "__main__":
    unittest.main()
