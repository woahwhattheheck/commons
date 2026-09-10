# SPDX-License-Identifier: Apache-2.0
import copy
import unittest

import livestock_dose as ld


def row(*market):
    return {"farmer": ["PASS"], "hands": [["PASS"]],
            "market": [list(order) for order in market]}


def route_fixture():
    route = [row() for _ in range(150)]
    route[0] = row(("BUY_PRODUCT", "WHEAT", 13))
    route[1] = row(("BUY_ANIMAL", "COW", 2), ("HIRE",))
    route[3] = row(("SELL", "WHEAT", 9), ("BUY_ANIMAL", "COW", 1))
    route[8] = row(("BUY_ANIMAL", "COW", 1), ("BUY_SEED", "MELON", 2))
    route[12] = row(("BUY_ANIMAL", "COW", 2))
    route[144] = row(("BUY_ANIMAL", "COW", 1))
    return route


class LivestockDoseTests(unittest.TestCase):
    def test_zero_is_identity(self):
        route = route_fixture()
        before = copy.deepcopy(route)
        report = ld.apply_route_dose(route, 0)
        self.assertEqual(route, before)
        self.assertFalse(report["changed"])
        self.assertEqual(report["reason"], "dose_zero")

    def test_first_two_single_unit_orders_only(self):
        route = route_fixture()
        before = copy.deepcopy(route)
        report = ld.apply_route_dose(route, 2)
        self.assertTrue(report["changed"])
        self.assertEqual(report["converted_units"], 2)
        self.assertEqual(route[3]["market"][1], ["BUY_ANIMAL", "SHEEP", 1])
        self.assertEqual(route[8]["market"][0], ["BUY_ANIMAL", "SHEEP", 1])
        # opening pair, later multi-unit order and post-window order stay COW
        self.assertEqual(route[1], before[1])
        self.assertEqual(route[12], before[12])
        self.assertEqual(route[144], before[144])
        # No action/queue shape or quantity changes.
        for i, (old, new) in enumerate(zip(before, route)):
            self.assertEqual(old["farmer"], new["farmer"], i)
            self.assertEqual(old["hands"], new["hands"], i)
            self.assertEqual(len(old["market"]), len(new["market"]), i)
            self.assertEqual([o[2:] for o in old["market"]],
                             [o[2:] for o in new["market"]], i)

    def test_partial_order_fails_closed(self):
        route = route_fixture()
        before = copy.deepcopy(route)
        report = ld.apply_route_dose(route, 3)
        self.assertFalse(report["changed"])
        self.assertEqual(report["reason"], "partial_order_would_change_cardinality")
        self.assertEqual(route, before)

    def test_insufficient_units_fails_closed(self):
        route = route_fixture()
        before = copy.deepcopy(route)
        report = ld.apply_route_dose(route, 99)
        self.assertFalse(report["changed"])
        self.assertEqual(report["reason"], "insufficient_eligible_units")
        self.assertEqual(route, before)

    def test_malformed_candidate_raises_before_mutation(self):
        route = route_fixture()
        route[8]["market"][0] = ["BUY_ANIMAL", "COW", True]
        before = copy.deepcopy(route)
        with self.assertRaises(ValueError):
            ld.apply_route_dose(route, 2)
        self.assertEqual(route, before)

    def test_patch_controller_changes_only_main(self):
        main = route_fixture()
        other = route_fixture()
        before_other = copy.deepcopy(other)
        controller = type("Controller", (), {})()
        controller.R = {ld.MAIN_ROUTE_ID: main, "other": other}
        report = ld.patch_controller(controller, 1)
        self.assertTrue(report["changed"])
        self.assertEqual(other, before_other)

    def test_install_is_lazy_and_reconstruction_safe(self):
        class Agent:
            def __init__(self):
                self.controller = None
                self.diagnostics = {}
                self.generation = 0

            def _initialize(self):
                self.generation += 1
                controller = type("Controller", (), {})()
                controller.R = {ld.MAIN_ROUTE_ID: route_fixture()}
                self.controller = controller
                return self.generation

        agent = Agent()
        install = ld.install_after_initialize(agent, 2)
        self.assertEqual(install["status"], "installed")
        self.assertIsNone(agent.controller)
        self.assertEqual(agent._initialize(), 1)
        first = agent.controller
        self.assertEqual(first.R[ld.MAIN_ROUTE_ID][3]["market"][1][1], "SHEEP")
        self.assertEqual(first.R[ld.MAIN_ROUTE_ID][8]["market"][0][1], "SHEEP")
        self.assertEqual(agent.diagnostics["v3_livestock_dose"]["converted_units"], 2)
        # A fresh controller built by a later canonical reconstruction receives
        # the same exact dose, not an accumulated second dose on the old route.
        self.assertEqual(agent._initialize(), 2)
        self.assertIsNot(agent.controller, first)
        self.assertEqual(agent.controller.R[ld.MAIN_ROUTE_ID][12]["market"][0][1], "COW")
        self.assertEqual(agent.diagnostics["v3_livestock_dose"]["converted_units"], 2)

    def test_reinstall_same_dose_is_idempotent(self):
        class Agent:
            def _initialize(self):
                pass
        agent = Agent()
        first = ld.install_after_initialize(agent, 1)
        second = ld.install_after_initialize(agent, 1)
        self.assertIs(first, second)
        with self.assertRaises(ValueError):
            ld.install_after_initialize(agent, 2)

    def test_bool_dose_rejected(self):
        with self.assertRaises(ValueError):
            ld.plan_dose(route_fixture(), True)


if __name__ == "__main__":
    unittest.main()
