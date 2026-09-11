# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import unittest

import candidate as c


def inventory(level=10000):
    return {item: level for item in c.PRODUCTS}


def obs(step, levels=None, shops=(), player=0):
    return {
        "step": step,
        "player": player,
        "market": {"inventory": dict(levels or inventory())},
        "town": {"unlocked_shops": list(shops)},
    }


NO_TOWN = {"townShopSellInterval": 9999, "townCenterSellInterval": 9999}


class PublicSupplyGateTests(unittest.TestCase):
    def test_own_requested_supply_is_not_rival_pressure(self):
        gate = c.PublicSupplyGate(lookback=8)
        before = inventory()
        self.assertFalse(gate.begin(obs(647, before)))
        gate.finish(obs(647, before), {"market": [["SELL", "MILK", 5]]}, NO_TOWN)
        after = inventory()
        after["MILK"] += 5
        self.assertTrue(gate.begin(obs(648, after)))
        self.assertEqual(gate.last_evidence[0]["MILK"], 0)

    def test_positive_residual_proves_rival_net_supply_and_guards(self):
        gate = c.PublicSupplyGate(lookback=8)
        before = inventory()
        gate.begin(obs(647, before))
        gate.finish(obs(647, before), {"market": [["SELL", "MILK", 5]]}, NO_TOWN)
        after = inventory()
        after["MILK"] += 9
        self.assertFalse(gate.begin(obs(648, after)))
        self.assertEqual(gate.last_evidence[0]["MILK"], 4)

    def test_pressure_expires_after_eight_clean_transitions(self):
        gate = c.PublicSupplyGate(lookback=8)
        level = inventory()
        gate.begin(obs(647, level))
        gate.finish(obs(647, level), {"market": []}, NO_TOWN)
        pressured = inventory()
        pressured["WOOL"] += 1
        self.assertFalse(gate.begin(obs(648, pressured)))
        gate.finish(obs(648, pressured), {"market": []}, NO_TOWN)
        for step in range(649, 656):
            self.assertFalse(gate.begin(obs(step, pressured)))
            gate.finish(obs(step, pressured), {"market": []}, NO_TOWN)
        self.assertTrue(gate.begin(obs(656, pressured)))

    def test_duplicate_single_product_shops_and_center_consumption(self):
        got = c._town_consumption(
            obs(648, inventory(), shops=("YARN_STORE", "YARN_STORE")), {}
        )
        self.assertEqual(got["WOOL"], 5)  # 2+2 from shops, +1 center
        self.assertEqual(got["MILK"], 1)
        self.assertEqual(got["FERTILIZER"], 0)

    def test_requested_sell_is_safe_upper_bound_even_if_unfillable(self):
        own = c._own_sell_upper_bound(
            {"market": [["SELL", "MILK", 99], ["SELL", "MILK", 2]]}
        )
        self.assertEqual(own["MILK"], 101)
        before = inventory()
        after = inventory()
        after["MILK"] += 7
        lower = c._rival_supply_lower_bound(
            before, after, own, {item: 0 for item in c.PRODUCTS}
        )
        self.assertLess(lower["MILK"], 0)

    def test_unknown_shop_fails_closed(self):
        gate = c.PublicSupplyGate()
        state = inventory()
        gate.begin(obs(647, state))
        gate.finish(obs(647, state, shops=("UNKNOWN",)), {"market": []}, {})
        self.assertFalse(gate.begin(obs(648, state)))

    def test_gap_and_rewind_fail_closed_and_reset_history(self):
        gate = c.PublicSupplyGate()
        state = inventory()
        gate.begin(obs(647, state))
        gate.finish(obs(647, state), {"market": []}, NO_TOWN)
        self.assertFalse(gate.begin(obs(650, state)))
        gate.finish(obs(650, state), {"market": []}, NO_TOWN)
        self.assertFalse(gate.begin(obs(649, state)))

    def test_malformed_public_inventory_fails_closed(self):
        gate = c.PublicSupplyGate()
        bad = obs(1, inventory())
        del bad["market"]["inventory"]["MILK"]
        self.assertFalse(gate.begin(bad))


if __name__ == "__main__":
    unittest.main()
