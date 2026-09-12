# SPDX-License-Identifier: Apache-2.0
import copy
import unittest

from test_v231_late_current import blank_tiles, observation, selected
from v231_late_current import _new_state
from v231_late_current_safe import V231LateCurrentABISafe


class TestV231LateRetrySafe(unittest.TestCase):
    def test_identical_purchase_retry_is_action_and_state_idempotent(self):
        arm = V231LateCurrentABISafe(enabled=True)
        obs = observation(step=216)
        parent = selected([["BUY_ANIMAL", "SHEEP", 1]])

        first = arm.transform(obs, parent)
        first_state = arm.states[0]
        second = arm.transform(obs, parent)
        second_state = arm.states[0]

        self.assertEqual(first, second)
        self.assertEqual(first["market"], [["BUY_ANIMAL", "COW", 1]])
        self.assertEqual(first_state, second_state)
        self.assertEqual(second_state["requested"], 1)
        self.assertEqual(second_state["pending_buy"], {"before": 0, "quantity": 1})

    def test_changed_retry_discards_abandoned_purchase_effects(self):
        arm = V231LateCurrentABISafe(enabled=True)
        obs = observation(step=216)
        sheep_buy = selected([["BUY_ANIMAL", "SHEEP", 1]])
        no_buy = selected()

        self.assertEqual(
            arm.transform(obs, sheep_buy)["market"], [["BUY_ANIMAL", "COW", 1]]
        )
        self.assertIsNotNone(arm.states[0]["pending_buy"])

        # The refreshed selected action is authoritative for the same public step.
        # Recompute from the pre-step snapshot instead of carrying the abandoned buy.
        self.assertEqual(arm.transform(obs, no_buy), no_buy)
        state = arm.states[0]
        self.assertIsNone(state["pending_buy"])
        self.assertEqual(state["requested"], 0)
        self.assertEqual(state["reserved"], 0)

        # A later COW appearing in the shed must not be claimed by the abandoned
        # attempt, so a parent SHEEP pickup stays untouched.
        next_obs = observation(
            step=217,
            shed={"COW": 1, "SHEEP": 1, "GOOSE": 0, "MILK": 0},
            farmer=(4, 4),
            inventories=[{}],
        )
        pickup = selected(farmer=["PICKUP", "SHEEP", 1])
        self.assertEqual(arm.transform(next_obs, pickup), pickup)
        self.assertEqual(arm.states[0]["confirmed"], 0)

    def test_identical_harvest_retry_does_not_double_credit(self):
        arm = V231LateCurrentABISafe(enabled=True)
        state = _new_state()
        state.update({
            "last": 219,
            "confirmed": 1,
            "sites": {(4, 4): 9},
        })
        arm._base._states[0] = copy.deepcopy(state)

        tiles = blank_tiles()
        tiles[4][4] = {
            "kind": "PASTURE",
            "animal": "COW",
            "placed_day": 9,
            "yield_units": 3,
        }
        obs = observation(
            step=220,
            shed={"COW": 0, "SHEEP": 0, "GOOSE": 0, "MILK": 10},
            farmer=(4, 4),
            inventories=[{}],
            tiles=tiles,
        )
        harvest = selected(
            market=[["SELL", "MILK", 2]],
            farmer=["HARVEST"],
        )

        first = arm.transform(obs, harvest)
        first_state = arm.states[0]
        second = arm.transform(obs, harvest)
        second_state = arm.states[0]

        self.assertEqual(first, second)
        self.assertEqual(first["market"], [["SELL", "MILK", 5]])
        self.assertEqual(first_state, second_state)
        self.assertEqual(second_state["extra_milk_harvested"], 3)
        self.assertEqual(second_state["extra_milk_sale_requests"], 3)
        self.assertEqual(second_state["milk_credit"], 0)

    def test_changed_harvest_retry_reverts_first_attempt_poststate(self):
        arm = V231LateCurrentABISafe(enabled=True)
        state = _new_state()
        state.update({
            "last": 219,
            "confirmed": 1,
            "sites": {(4, 4): 9},
        })
        arm._base._states[0] = copy.deepcopy(state)

        tiles = blank_tiles()
        tiles[4][4] = {
            "kind": "PASTURE",
            "animal": "COW",
            "placed_day": 9,
            "yield_units": 3,
        }
        obs = observation(
            step=220,
            shed={"COW": 0, "SHEEP": 0, "GOOSE": 0, "MILK": 10},
            farmer=(4, 4),
            inventories=[{}],
            tiles=tiles,
        )
        harvest = selected(market=[["SELL", "MILK", 2]], farmer=["HARVEST"])
        refreshed = selected(market=[["SELL", "MILK", 2]], farmer=["PASS"])

        self.assertEqual(arm.transform(obs, harvest)["market"], [["SELL", "MILK", 5]])
        self.assertEqual(arm.transform(obs, refreshed), refreshed)
        state_after = arm.states[0]
        self.assertEqual(state_after["extra_milk_harvested"], 0)
        self.assertEqual(state_after["extra_milk_sale_requests"], 0)
        self.assertEqual(state_after["milk_credit"], 0)
        self.assertEqual(state_after["sites"], {(4, 4): 9})

    def test_rewind_starts_fresh_epoch(self):
        arm = V231LateCurrentABISafe(enabled=True)
        arm.transform(observation(step=216), selected([["BUY_ANIMAL", "SHEEP", 1]]))
        self.assertEqual(arm.states[0]["requested"], 1)

        rewind = selected([["BUY_ANIMAL", "SHEEP", 1]])
        self.assertEqual(arm.transform(observation(step=0), rewind), rewind)
        state = arm.states[0]
        self.assertEqual(state["requested"], 0)
        self.assertIsNone(state["pending_buy"])
        self.assertEqual(state["last"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
