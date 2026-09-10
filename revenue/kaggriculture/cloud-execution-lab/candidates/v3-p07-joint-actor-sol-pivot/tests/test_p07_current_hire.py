# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
import unittest

import p07_atomic
from p07_current_hire import classify_current_hire, install_current_hire_window
from spatial_tempo import SpatialTempo, unit
from test_joint_assignment import crossing_fixture, row


class Controller:
    def __init__(self, route):
        self.cur = 0
        self.R = {0: route}


class CurrentHireWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_current_hire_window(p07_atomic)

    def setUp(self):
        mechanics, observation, route = crossing_fixture()
        while len(route) < 720:
            route.append(row())
        observation.update(step=0, day=0, hour=0)
        self.observation = observation
        self.route = route
        self.controller = Controller(route)
        self.spatial = SpatialTempo(mechanics)
        self.spatial.configuration = {
            "turnsPerDay": 24,
            "episodeSteps": 720,
            "shedCapacity": 100,
            "maxMarketOrdersPerTurn": 10,
        }
        self.instance = SimpleNamespace(
            spatial=self.spatial,
            quadrant=SimpleNamespace(active=False),
        )
        p07_atomic.install_spatial_hooks(
            self.spatial, self.instance, enabled=True
        )
        self.selected = deepcopy(route[0])

    def set_current(self, market, extra_hands=()):
        self.selected["market"] = deepcopy(market)
        self.route[0]["market"] = deepcopy(market)
        for action in extra_hands:
            self.selected["hands"].append(list(action))
            self.route[0]["hands"].append(list(action))

    def propose(self):
        return p07_atomic.reconcile(
            self.spatial,
            self.observation,
            deepcopy(self.selected),
            self.controller,
        )

    def test_old_blanket_veto_is_killed_and_all_nonpair_bytes_survive(self):
        self.set_current([["HIRE"]], extra_hands=(("NORTH",),))
        original_market = deepcopy(self.selected["market"])
        original_tail = deepcopy(self.selected["hands"][1:])
        output = self.propose()
        report = self.spatial.p07_report
        self.assertTrue(report["changed"], report)
        pair = tuple(report["pair"])
        self.assertTrue(
            any(unit(output, actor) != unit(self.selected, actor) for actor in pair)
        )
        self.assertEqual(output["market"], original_market)
        self.assertEqual(output["hands"][1:], original_tail)
        self.assertEqual(self.route[0]["market"], original_market)
        self.assertEqual(self.route[0]["hands"][1:], original_tail)
        receipt = report["current_hire_window"]
        self.assertEqual(receipt["existing_actor_count"], 2)
        self.assertEqual(receipt["active_hires"], 1)
        self.assertEqual(receipt["extra_actor_actions"], 1)

    def test_non_hire_current_market_remains_a_hard_boundary(self):
        self.set_current([["SELL", "WHEAT", 1]])
        original = deepcopy(self.route)
        output = self.propose()
        self.assertEqual(output, self.selected)
        self.assertEqual(self.route, original)
        self.assertEqual(
            self.spatial.p07_report["reason"],
            "current_non_hire_market_boundary",
        )

    def test_inactive_suffix_hire_is_not_misclassified_as_executable(self):
        self.spatial.configuration["maxMarketOrdersPerTurn"] = 1
        self.set_current([["HIRE"], ["HIRE"]])
        output = self.propose()
        self.assertEqual(output, self.selected)
        self.assertEqual(
            self.spatial.p07_report["reason"],
            "inactive_suffix_market_boundary",
        )

    def test_bool_and_zero_prefix_carriers_fail_closed(self):
        for invalid in (True, 0):
            with self.subTest(invalid=invalid):
                receipt = classify_current_hire(
                    {"market": [["HIRE"]], "hands": [[]]},
                    {"market": [["HIRE"]], "hands": [[]]},
                    {"maxMarketOrdersPerTurn": invalid},
                    2,
                )
                self.assertFalse(receipt["admitted"])
                self.assertEqual(
                    receipt["reason"], "unsupported_market_prefix_config"
                )

    def test_excess_new_actor_action_tail_fails_closed(self):
        self.set_current(
            [["HIRE"]],
            extra_hands=(("NORTH",), ("SOUTH",)),
        )
        original = deepcopy(self.route)
        output = self.propose()
        self.assertEqual(output, self.selected)
        self.assertEqual(self.route, original)
        self.assertEqual(
            self.spatial.p07_report["reason"], "excess_new_actor_actions"
        )

    def test_market_and_new_actor_tail_must_bind_to_route_source(self):
        receipt = classify_current_hire(
            {"market": [["HIRE"]], "hands": [["PASS"], ["NORTH"]]},
            {"market": [["HIRE"]], "hands": [["PASS"], ["SOUTH"]]},
            {"maxMarketOrdersPerTurn": 10},
            2,
        )
        self.assertFalse(receipt["admitted"])
        self.assertEqual(receipt["reason"], "new_actor_tail_source_mismatch")

        receipt = classify_current_hire(
            {"market": [["HIRE"]], "hands": [["PASS"]]},
            {"market": [], "hands": [["PASS"]]},
            {"maxMarketOrdersPerTurn": 10},
            2,
        )
        self.assertFalse(receipt["admitted"])
        self.assertEqual(receipt["reason"], "current_market_source_mismatch")

    def test_future_hire_is_still_visible_to_exact_primitive_and_rejected(self):
        self.set_current([["HIRE"]])
        self.route[5]["market"] = [["HIRE"]]
        original = deepcopy(self.route)
        output = self.propose()
        self.assertEqual(output, self.selected)
        self.assertEqual(self.route, original)
        self.assertFalse(self.spatial.p07_report["changed"])
        self.assertEqual(self.spatial.p07_report["reason"], "market_boundary")

    def test_certified_but_dormant_row_preserves_route_object_identity(self):
        mechanics, observation, route = crossing_fixture(aligned=True)
        while len(route) < 720:
            route.append(row())
        observation.update(step=0, day=0, hour=0)
        route[0]["market"] = [["HIRE"]]
        selected = deepcopy(route[0])
        controller = Controller(route)
        spatial = SpatialTempo(mechanics)
        spatial.configuration = {
            "turnsPerDay": 24,
            "episodeSteps": 720,
            "shedCapacity": 100,
            "maxMarketOrdersPerTurn": 10,
        }
        instance = SimpleNamespace(
            spatial=spatial,
            quadrant=SimpleNamespace(active=False),
        )
        p07_atomic.install_spatial_hooks(spatial, instance, enabled=True)
        original_row = route[0]
        output = p07_atomic.reconcile(
            spatial, observation, deepcopy(selected), controller
        )
        self.assertIs(route[0], original_row)
        self.assertEqual(output, selected)
        self.assertFalse(spatial.p07_report["changed"])
        self.assertIn("current_hire_window", spatial.p07_report)

    def test_install_is_idempotent(self):
        wrapped = p07_atomic.reconcile
        install_current_hire_window(p07_atomic)
        self.assertIs(p07_atomic.reconcile, wrapped)


if __name__ == "__main__":
    unittest.main()
