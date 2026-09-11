#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
V3 = HERE.parents[1]
C6 = V3 / "experiments" / "c6_fertilizer_sale_cap"
OVERLAY = V3 / "overlay"
for path in (C6, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import candidate as c6  # noqa: E402


def observation(*, day=24, inventories=None):
    return {
        "step": day * 24,
        "player": 0,
        "private": {"inventories": list(inventories or [{"FERTILIZER": 0}])},
    }


class C6PickupRequestedReserveRepairTests(unittest.TestCase):
    def setUp(self):
        self.saved_states = c6.base._V219_STATES
        c6.base._V219_STATES = {}

    def tearDown(self):
        c6.base._V219_STATES = self.saved_states

    def test_pickup_requested_role_contributes_zero_future_loader_reserve(self):
        c6.base._V219_STATES[0] = {
            "committed": True,
            "day": 24,
            "workers": {
                0: {
                    "kind": "crop",
                    "needs_fertilizer": True,
                    "loaded": False,
                    "pickup_requested": True,
                },
            },
        }
        self.assertEqual(c6.v219_fertilizer_reserve(observation()), 0)

    def test_mixed_roles_reserve_only_worker_without_current_pickup(self):
        c6.base._V219_STATES[0] = {
            "committed": True,
            "day": 24,
            "workers": {
                0: {
                    "kind": "crop",
                    "needs_fertilizer": True,
                    "loaded": False,
                    "pickup_requested": True,
                },
                1: {
                    "kind": "crop",
                    "needs_fertilizer": True,
                    "loaded": False,
                    "pickup_requested": False,
                },
            },
        }
        obs = observation(inventories=[{"FERTILIZER": 0}, {"FERTILIZER": 1}])
        self.assertEqual(c6.v219_fertilizer_reserve(obs), 4)

    def test_present_non_bool_pickup_requested_fails_closed(self):
        for poisoned in (1, 0, 1.0, "true", None, [], {}):
            with self.subTest(poisoned=poisoned):
                c6.base._V219_STATES[0] = {
                    "committed": True,
                    "day": 24,
                    "workers": {
                        0: {
                            "kind": "crop",
                            "needs_fertilizer": True,
                            "loaded": False,
                            "pickup_requested": poisoned,
                        },
                    },
                }
                self.assertIsNone(c6.v219_fertilizer_reserve(observation()))

    def test_missing_pickup_requested_preserves_existing_future_reserve(self):
        c6.base._V219_STATES[0] = {
            "committed": True,
            "day": 24,
            "workers": {
                0: {"kind": "crop", "needs_fertilizer": True, "loaded": False},
            },
        }
        self.assertEqual(c6.v219_fertilizer_reserve(observation()), 5)


if __name__ == "__main__":
    unittest.main()
