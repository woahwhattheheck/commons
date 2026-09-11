# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
OVERLAY = HERE.parent / "overlay"
for path in (HERE, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import h7_r04_rival_response as h7  # noqa: E402


def obs(*, step=10, own_money=3000, own_unlocked=None, rival_unlocked=None, prices=None):
    own = {
        "money": own_money,
        "unlocked_quadrants": list(own_unlocked or ["NW"]),
        "tiles": [[None]],
        "hands": [],
    }
    rival = {
        "money": 3000,
        "unlocked_quadrants": list(rival_unlocked or ["NW", "NE"]),
        "tiles": [[None]],
        "hands": [],
    }
    return {
        "step": step,
        "player": 0,
        "farms": [own, rival],
        "market": {"prices": dict(prices or {"WHEAT": 10})},
    }


def parent_with(action):
    def parent(_observation, _configuration=None):
        return action
    return parent


class H7R04RivalResponseTests(unittest.TestCase):
    def test_disabled_is_exact_parent_output_identity(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "WHEAT", 1]]}
        arm = h7.install(parent_with(action), enabled=False)
        self.assertIs(arm(obs(), {"maxMarketOrdersPerTurn": 10}), action)
        self.assertEqual(arm.telemetry["changed"], 0)
        self.assertEqual(arm.telemetry["reasons"]["OFF"], 1)

    def test_public_early_expander_appends_land_after_final_r04_rows(self):
        final_r04 = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "STRAWBERRY", 4], ["SELL", "WOOL", 3], ["HIRE"]],
        }
        before = deepcopy(final_r04)
        arm = h7.install(parent_with(final_r04), enabled=True)
        out = arm(obs(own_money=1000), {"maxMarketOrdersPerTurn": 10})
        self.assertEqual(final_r04, before)
        self.assertEqual(out["market"][:-1], before["market"])
        self.assertEqual(out["market"][-1], ["BUY_LAND"])
        self.assertEqual(arm.telemetry["changed"], 1)
        self.assertEqual(arm.telemetry["archetypes"]["EARLY_EXPANDER"], 1)

    def test_full_final_queue_fails_closed_instead_of_displacing_flush_row(self):
        rows = [["SELL", "STRAWBERRY", i + 1] for i in range(10)]
        action = {"farmer": ["PASS"], "hands": [], "market": deepcopy(rows)}
        arm = h7.install(parent_with(action), enabled=True)
        out = arm(obs(step=45), {"maxMarketOrdersPerTurn": 10})
        self.assertIs(out, action)
        self.assertEqual(out["market"], rows)
        self.assertEqual(arm.telemetry["reasons"]["EARLY_EXPANDER_NO_FREE_MARKET_SLOT"], 1)

    def test_ninth_existing_row_keeps_every_parent_row_and_land_is_tenth(self):
        rows = [["SELL", "MILK", i + 1] for i in range(9)]
        action = {"farmer": ["PASS"], "hands": [], "market": deepcopy(rows)}
        arm = h7.install(parent_with(action), enabled=True)
        out = arm(obs(step=45), {"maxMarketOrdersPerTurn": 10})
        self.assertEqual(out["market"][:9], rows)
        self.assertEqual(out["market"][9], ["BUY_LAND"])

    def test_existing_land_order_is_never_duplicated(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["BUY_LAND"], ["SELL", "WHEAT", 1]]}
        arm = h7.install(parent_with(action), enabled=True)
        out = arm(obs(), {"maxMarketOrdersPerTurn": 10})
        self.assertIs(out, action)
        self.assertEqual(out["market"].count(["BUY_LAND"]), 1)

    def test_cutoff_step_is_identity(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        arm = h7.install(parent_with(action), enabled=True, early_expander_step=144)
        self.assertIs(arm(obs(step=145), {"maxMarketOrdersPerTurn": 10}), action)
        self.assertEqual(arm.telemetry["changed"], 0)

    def test_cash_floor_blocks_unfunded_response(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        arm = h7.install(parent_with(action), enabled=True, land_cash_floor=500)
        out = arm(obs(own_money=1499), {"maxMarketOrdersPerTurn": 10})
        self.assertIs(out, action)
        self.assertEqual(arm.telemetry["reasons"]["EARLY_EXPANDER_CASH_FLOOR"], 1)

    def test_own_expansion_blocks_extra_land(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        arm = h7.install(parent_with(action), enabled=True)
        out = arm(obs(own_unlocked=["NW", "NE"]), {"maxMarketOrdersPerTurn": 10})
        self.assertIs(out, action)
        self.assertEqual(arm.telemetry["reasons"]["EARLY_EXPANDER_NO_EDIT"], 1)

    def test_new_episode_resets_price_history_per_player(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        arm = h7.install(parent_with(action), enabled=True)
        arm(obs(step=200, rival_unlocked=["NW"], prices={"WHEAT": 40}), {"maxMarketOrdersPerTurn": 10})
        arm(obs(step=201, rival_unlocked=["NW"], prices={"WHEAT": 10}), {"maxMarketOrdersPerTurn": 10})
        self.assertEqual(arm.telemetry["archetypes"]["AGGRESSIVE_MARKET_DUMPER"], 1)
        arm(obs(step=0, rival_unlocked=["NW"], prices={"WHEAT": 10}), {"maxMarketOrdersPerTurn": 10})
        self.assertEqual(arm.telemetry["archetypes"]["AGGRESSIVE_MARKET_DUMPER"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
