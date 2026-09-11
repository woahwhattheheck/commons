from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import candidate as b7  # noqa: E402


PRODUCTS = tuple(b7.base.PRODUCTS)
BLANK = {"farmer": ["PASS"], "hands": [], "market": []}


class FakeTape:
    def __init__(self, events=None):
        self.events = dict(events or {})

    def __getitem__(self, step):
        return self.events.get(step, BLANK)


class FakePolicy:
    def __init__(self, plan=5, events=None):
        self.players = {0: SimpleNamespace(plan=plan)}
        self.tapes = [FakeTape() for _ in range(13)]
        self.tapes[plan] = FakeTape(events)


def observation(step=600, *, shed=None, inventory=None):
    shed_values = {item: 0 for item in PRODUCTS}
    shed_values.update(shed or {})
    tiles = [[None for _ in range(10)] for _ in range(10)]
    return {
        "step": step,
        "player": 0,
        "farms": [{
            "tiles": tiles,
            "farmer": [4, 4],
            "hands": [],
            "money": 20000,
            "unlocked_quadrants": ["NW", "NE", "SW", "SE"],
        }],
        "private": {
            "inventories": [dict(inventory or {})],
            "shed": shed_values,
        },
        "market": {"prices": {item: 20 for item in PRODUCTS}, "inventory": {}},
        "town": {"unlocked_shops": []},
    }


def action(*, market=None, farmer=None):
    return {
        "farmer": list(farmer or ["PASS"]),
        "hands": [],
        "market": [list(row) if row else row for row in (market or [])],
    }


def v219_pending(step=600, fertilizer=True):
    return {"pending": {"step": step, "fertilizer": fertilizer}}


class RoomGuardTests(unittest.TestCase):
    def setUp(self):
        b7.reset_b7_report()
        self.policy = FakePolicy()

    def guard(self, obs, parent, *, state=None, enabled=True, policy=None, configuration=None):
        return b7.room_guard(
            obs,
            parent,
            enabled=enabled,
            policy=self.policy if policy is None else policy,
            v219_state=v219_pending(obs["step"]) if state is None else state,
            configuration=configuration,
        )

    def test_exact_v31_capacity_baseline_is_pinned(self):
        self.assertEqual(b7.base.SHED_CAPACITY, 100)
        self.assertEqual(b7.base.MAX_ORDERS, 10)
        self.assertEqual(b7.V219_FERTILIZER_ROW, ["BUY_PRODUCT", "FERTILIZER", 10])
        self.assertIs(b7.B7_ENABLED, False)

    def test_disabled_is_exact_identity(self):
        parent = action(market=[["BUY_PRODUCT", "FERTILIZER", 10]])
        result = self.guard(observation(shed={"CARROT": 100}), parent, enabled=False)
        self.assertIs(result, parent)
        self.assertEqual(b7.B7_REPORT["activations"], 0)

    def test_only_v219_fertilizer_causes_overflow_and_row_index_is_preserved(self):
        parent = action(market=[
            ["BUY_SEED", "TOMATO", 10],
            ["BUY_PRODUCT", "FERTILIZER", 10],
            ["BUY_PRODUCT", "WHEAT", 5],
            ["HIRE"],
        ])
        result = self.guard(observation(shed={"CARROT": 86}), parent)
        self.assertIsNot(result, parent)
        self.assertEqual(result["market"], [
            ["BUY_SEED", "TOMATO", 10],
            [],
            ["BUY_PRODUCT", "WHEAT", 5],
            ["HIRE"],
        ])
        self.assertEqual(len(result["market"]), len(parent["market"]))
        self.assertEqual(result["market"][2:], parent["market"][2:])
        self.assertEqual(b7.B7_REPORT["activations"], 1)
        self.assertEqual(b7.B7_REPORT["guarded_units"], 10)

    def test_no_overflow_keeps_parent_identity(self):
        parent = action(market=[
            ["BUY_PRODUCT", "FERTILIZER", 10],
            ["BUY_PRODUCT", "WHEAT", 5],
        ])
        result = self.guard(observation(shed={"CARROT": 80}), parent)
        self.assertIs(result, parent)
        self.assertEqual(b7.B7_REPORT["activations"], 0)

    def test_other_purchases_already_overflow_fails_closed(self):
        parent = action(market=[
            ["BUY_PRODUCT", "FERTILIZER", 10],
            ["BUY_PRODUCT", "WHEAT", 5],
        ])
        result = self.guard(observation(shed={"CARROT": 96}), parent)
        self.assertIs(result, parent)
        self.assertEqual(b7.B7_REPORT["other_overflow_declines"], 1)
        self.assertEqual(b7.B7_REPORT["activations"], 0)

    def test_native_identical_row_makes_provenance_ambiguous(self):
        native = {600: {
            "farmer": ["PASS"], "hands": [],
            "market": [["BUY_PRODUCT", "FERTILIZER", 10]],
        }}
        policy = FakePolicy(events=native)
        parent = action(market=[["BUY_PRODUCT", "FERTILIZER", 10]])
        result = self.guard(observation(shed={"CARROT": 95}), parent, policy=policy)
        self.assertIs(result, parent)
        self.assertEqual(b7.B7_REPORT["native_collision_declines"], 1)

    def test_duplicate_final_rows_fail_closed(self):
        parent = action(market=[
            ["BUY_PRODUCT", "FERTILIZER", 10],
            ["BUY_PRODUCT", "FERTILIZER", 10],
        ])
        result = self.guard(observation(shed={"CARROT": 85}), parent)
        self.assertIs(result, parent)
        self.assertEqual(b7.B7_REPORT["ambiguous_row_declines"], 1)

    def test_without_same_step_v219_pending_request_guard_does_nothing(self):
        parent = action(market=[["BUY_PRODUCT", "FERTILIZER", 10]])
        stale = v219_pending(step=599)
        result = self.guard(observation(shed={"CARROT": 95}), parent, state=stale)
        self.assertIs(result, parent)
        self.assertEqual(b7.B7_REPORT["v219_fertilizer_requests_seen"], 0)

    def test_projected_pickup_room_is_credited_before_guard(self):
        parent = action(
            farmer=["PICKUP", "CARROT", 15],
            market=[
                ["BUY_PRODUCT", "FERTILIZER", 10],
                ["BUY_PRODUCT", "WHEAT", 5],
            ],
        )
        result = self.guard(observation(shed={"CARROT": 96}), parent)
        self.assertIs(result, parent)
        self.assertEqual(b7.B7_REPORT["activations"], 0)

    def test_projected_drop_can_make_v219_purchase_the_capacity_crossing(self):
        parent = action(
            farmer=["DROP"],
            market=[
                ["BUY_PRODUCT", "FERTILIZER", 10],
                ["BUY_PRODUCT", "WHEAT", 5],
            ],
        )
        result = self.guard(
            observation(shed={"CARROT": 80}, inventory={"EGG": 10}),
            parent,
        )
        self.assertEqual(result["market"][0], [])
        self.assertEqual(result["market"][1], ["BUY_PRODUCT", "WHEAT", 5])

    def test_nondefault_shed_configuration_fails_closed(self):
        parent = action(market=[["BUY_PRODUCT", "FERTILIZER", 10]])
        result = self.guard(
            observation(shed={"CARROT": 95}),
            parent,
            configuration={"shedCapacity": 120},
        )
        self.assertIs(result, parent)
        self.assertEqual(b7.B7_REPORT["configuration_declines"], 1)

    def test_missing_route_custody_fails_closed(self):
        parent = action(market=[["BUY_PRODUCT", "FERTILIZER", 10]])
        result = self.guard(observation(shed={"CARROT": 95}), parent, policy=False)
        self.assertIs(result, parent)
        self.assertEqual(b7.B7_REPORT["native_collision_declines"], 1)


if __name__ == "__main__":
    unittest.main()
