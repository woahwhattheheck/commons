# SPDX-License-Identifier: Apache-2.0
"""Router-level regression for B10/M1 authorship + captured-parent provenance.

A final WHEAT BUY may already belong to a predecessor controller. The keyless
B10/M1 bridge is legal only when the current M1 helper actually authored a new
action object; an inherited parent BUY must stay on canonical B10's cash-spend
veto path. When M1 does author, the exact pre-M1 parent must be forwarded to the
prefix-provenance helper.
"""
from __future__ import annotations

import copy
import unittest
from unittest import mock

import r04_b10_m1_bridge as bridge
import r04_b10_public_supply_order as b10
import r04_full_router as r04
import r04_m1_wheat_trade as m1


CONFIG = {
    "episodeSteps": 720,
    "boardSize": 10,
    "turnsPerDay": 24,
    "shedCapacity": 100,
    "maxMarketOrdersPerTurn": 10,
    "townShopUnlockInterval": 3,
    "townShopSellInterval": 4,
    "townCenterSellInterval": 24,
}


def observation():
    return {
        "step": 49,
        "player": 0,
        "farms": [{"money": 3000}, {"money": 3000}],
        "market": {
            "inventory": {"WHEAT": 100, "WOOL": 10003},
            "prices": {"WHEAT": 21, "WOOL": 10, "MILK": 10},
        },
        "private": {"shed": {}},
        "town": {"unlocked_shops": []},
    }


def parent_with_wheat_buy():
    return {
        "farmer": ["PASS"],
        "hands": [],
        "market": [
            ["SELL", "MILK", 1],
            ["SELL", "WOOL", 1],
            ["BUY_PRODUCT", "WHEAT", 4],
        ],
    }


_FLAG_NAMES = (
    "MIRROR_HORIZON",
    "TERMINAL_FERTILIZER",
    "GOOSE_RESCUE",
    "PLACE_DELIVERY",
    "GOOSE_PASS_RESCUE",
    "H3B_SHEEP_CLIP",
    "H3E_COW_FEED_RECYCLE",
    "V233_EOD_SERVICE",
    "B10_PUBLIC_SUPPLY_ORDER",
    "DEAD_SELL_SLOT",
    "ADVANCE_SLOT_VALUE",
    "EOD_CAPACITY_RESCUE",
    "M1_WHEAT_TRADE",
    "C5_WHEAT_DEMAND",
    "S4_ROUTE12_SEED_RESERVE",
)


class B10M1AuthorshipTests(unittest.TestCase):
    def setUp(self):
        self._flags = {name: getattr(r04, name) for name in _FLAG_NAMES}
        for name in _FLAG_NAMES:
            setattr(r04, name, False)
        r04.M1_WHEAT_TRADE = True
        r04.B10_PUBLIC_SUPPLY_ORDER = True

    def tearDown(self):
        for name, value in self._flags.items():
            setattr(r04, name, value)

    def _router(self, parent, m1_result):
        with (
            mock.patch.object(r04, "_v3_core", return_value=parent),
            mock.patch.object(r04._POLICY, "players", {0: object()}),
            mock.patch.object(r04, "_policy_tape", return_value=[]),
            mock.patch.object(m1, "apply_m1_wheat_trade", return_value=m1_result) as m1_call,
            mock.patch.object(bridge, "apply_b10_m1_bridge", return_value=m1_result) as bridge_call,
            mock.patch.object(b10, "apply_public_supply_order", return_value=m1_result) as b10_call,
        ):
            result = r04.v3_agent(observation(), CONFIG)
        self.assertEqual(m1_call.call_count, 1)
        return result, bridge_call, b10_call

    def test_predecessor_authored_final_wheat_buy_never_uses_bridge(self):
        parent = parent_with_wheat_buy()
        result, bridge_call, b10_call = self._router(parent, parent)
        self.assertIs(result, parent)
        bridge_call.assert_not_called()
        b10_call.assert_called_once_with(
            mock.ANY, parent, CONFIG, enabled=True,
        )

    def test_actual_m1_new_object_forwards_exact_parent_to_bridge(self):
        parent = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "MILK", 1], ["SELL", "WOOL", 1]],
        }
        authored = copy.deepcopy(parent)
        authored["market"].append(["BUY_PRODUCT", "WHEAT", 4])
        result, bridge_call, b10_call = self._router(parent, authored)
        self.assertIs(result, authored)
        bridge_call.assert_called_once_with(
            mock.ANY, authored, CONFIG, m1_parent_action=parent,
        )
        b10_call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
