# SPDX-License-Identifier: Apache-2.0
import unittest

from route_matrix import force_plan


BASE = b'''ROUTE_STEP = 144
FINAL_PLAN_STEP = 648
SHOP_PLANS = {("A", "B"): 3}

class State:
    plan = 0

def choose(state, observation, step):
    if step == ROUTE_STEP:
        shops = observation["town"]["unlocked_shops"]
        state.plan = SHOP_PLANS.get(tuple(shops[:2]), 0)
    if step == FINAL_PLAN_STEP:
        state.plan = 2
    return state.plan
'''


class RouteMatrixTests(unittest.TestCase):
    def test_forces_only_lookup_rhs(self):
        changed = force_plan(BASE, 7)
        expected = BASE.replace(
            b"SHOP_PLANS.get(tuple(shops[:2]), 0)",
            b"7",
            1,
        )
        self.assertEqual(changed, expected)
        self.assertIn(
            b"if step == FINAL_PLAN_STEP:\n        state.plan = 2",
            changed,
        )

    def test_all_plan_indices(self):
        for plan in range(13):
            changed = force_plan(BASE, plan)
            self.assertIn(f"state.plan = {plan}\n".encode(), changed)

    def test_rejects_bool_and_range(self):
        for value in (True, False, -1, 13, 99):
            with self.assertRaises(ValueError):
                force_plan(BASE, value)

    def test_rejects_wrong_route_step(self):
        poisoned = BASE.replace(b"ROUTE_STEP = 144", b"ROUTE_STEP = 143")
        with self.assertRaises(ValueError):
            force_plan(poisoned, 3)

    def test_rejects_missing_terminal_plan2(self):
        poisoned = BASE.replace(b"state.plan = 2", b"state.plan = 1")
        with self.assertRaises(ValueError):
            force_plan(poisoned, 3)

    def test_rejects_lookup_outside_route_guard(self):
        poisoned = BASE.replace(
            b"if step == ROUTE_STEP:\n",
            b"if step == 100:\n",
        )
        with self.assertRaises(ValueError):
            force_plan(poisoned, 3)

    def test_rejects_duplicate_lookup(self):
        poisoned = BASE.replace(
            b"    if step == FINAL_PLAN_STEP:\n",
            b"    state.plan = SHOP_PLANS.get((\"A\", \"B\"), 0)\n"
            b"    if step == FINAL_PLAN_STEP:\n",
        )
        with self.assertRaises(ValueError):
            force_plan(poisoned, 3)

    def test_supports_legacy_subscript_shape(self):
        source = BASE.replace(
            b"SHOP_PLANS.get(tuple(shops[:2]), 0)",
            b"SHOP_PLANS[tuple(shops[:2])]",
        )
        changed = force_plan(source, 12)
        self.assertIn(b"state.plan = 12", changed)


if __name__ == "__main__":
    unittest.main()
