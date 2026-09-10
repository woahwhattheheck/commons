# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
import json
import os
from pathlib import Path
import tempfile
import unittest

import p07_atomic
from p07_current_hire import classify_current_hire, install_current_hire_window
from spatial_tempo import SpatialTempo, unit
from test_joint_assignment import crossing_fixture, row


class Controller:
    def __init__(self, route):
        self.cur = 0
        self.R = {0: route}


def fixed_hire(farm, private, board, mult=1):
    """Test primitive with the same append-after-units contract as official HIRE."""
    farm.setdefault("hands", []).append([2, 2])
    private.setdefault("inventories", []).append({})


class CurrentHireWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_current_hire_window(p07_atomic)

    def setUp(self):
        mechanics, observation, route = crossing_fixture()
        mechanics._do_hire = fixed_hire
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
            "farmHandCostMult": 1,
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
        self.assertTrue(receipt["replay"]["accepted"])
        self.assertTrue(receipt["final_market_bound"])
        self.assertEqual(
            self.spatial._p07_pending["required_market"], [["HIRE"]]
        )
        guarded = self.spatial.guard_returned(self.observation, output)
        self.assertEqual(guarded, output)
        self.assertEqual(
            self.spatial._p07_pending["guard_decision"], "commit_pair"
        )
        self.assertTrue(self.spatial._p07_pending["guard_pair_actions"])
        self.assertTrue(self.spatial._p07_pending["guard_market_binding"])

    def test_full_replay_rejects_spawn_difference_hidden_by_unit_only_proof(self):
        def position_sensitive_hire(farm, private, board, mult=1):
            # Baseline step-0 movements leave all sites empty and choose (4,0).
            # The travel-reduced candidate remains on both edge sites and
            # chooses (2,0).  The unit-only predecessor cannot see this.
            sites = [(4, 0), (2, 0), (0, 0)]
            occupied = {site: 0 for site in sites}
            for position in [farm["farmer"], *farm.get("hands", [])]:
                key = tuple(position)
                if key in occupied:
                    occupied[key] += 1
            chosen = min(sites, key=lambda site: (occupied[site], sites.index(site)))
            farm["hands"].append(list(chosen))
            private["inventories"].append({})

        self.spatial.m._do_hire = position_sensitive_hire
        self.set_current([["HIRE"]])
        original_refs = list(self.route[:15])
        original = deepcopy(self.route)
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "trace.jsonl"
            previous = os.environ.get("TITAN_P07_LOG")
            os.environ["TITAN_P07_LOG"] = str(log)
            try:
                output = self.propose()
            finally:
                if previous is None:
                    os.environ.pop("TITAN_P07_LOG", None)
                else:
                    os.environ["TITAN_P07_LOG"] = previous
            trace = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(len(trace), 1)
        self.assertFalse(trace[0]["changed"])
        self.assertEqual(
            trace[0]["reason"], "current_hire_full_replay_mismatch"
        )
        self.assertEqual(output, self.selected)
        self.assertEqual(self.route, original)
        self.assertTrue(all(self.route[i] is original_refs[i] for i in range(15)))
        self.assertEqual(self.spatial.plans, {})
        self.assertEqual(self.spatial.active, {})
        self.assertIsNone(self.spatial._p07_pending)
        report = self.spatial.p07_report
        self.assertFalse(report["changed"])
        self.assertEqual(report["reason"], "current_hire_full_replay_mismatch")
        window = report["current_hire_window"]
        self.assertTrue(window["rolled_back_exact_proposal"])
        self.assertFalse(window["replay"]["accepted"])
        self.assertFalse(window["replay"]["hands_equal"])

    def test_final_market_change_rolls_back_both_pair_actions(self):
        self.set_current([["HIRE"]])
        output = self.propose()
        pending = deepcopy(self.spatial._p07_pending)
        pair = tuple(pending["pair"])
        altered = deepcopy(output)
        altered["market"] = []
        guarded = self.spatial.guard_returned(self.observation, altered)
        for worker in pair:
            self.assertEqual(
                unit(guarded, worker), pending["baseline_current"][worker]
            )
        self.assertEqual(guarded["market"], [])
        self.assertEqual(
            self.spatial._p07_pending["guard_decision"], "rollback_pair"
        )
        self.assertTrue(self.spatial._p07_pending["guard_pair_actions"])
        self.assertFalse(self.spatial._p07_pending["guard_market_binding"])

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

    def test_official_none_and_empty_blanks_are_inert(self):
        receipt = classify_current_hire(
            {"market": [None, [], ["HIRE"]], "hands": [["PASS"]]},
            {"market": [None, [], ["HIRE"]], "hands": [["PASS"]]},
            {"maxMarketOrdersPerTurn": 10},
            2,
        )
        self.assertTrue(receipt["admitted"])
        self.assertEqual(receipt["active_hires"], 1)

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
        mechanics._do_hire = fixed_hire
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
            "farmHandCostMult": 1,
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

    def test_missing_hire_primitive_fails_closed_after_exact_proposal(self):
        delattr(self.spatial.m, "_do_hire")
        self.set_current([["HIRE"]])
        original = deepcopy(self.route)
        output = self.propose()
        self.assertEqual(output, self.selected)
        self.assertEqual(self.route, original)
        self.assertFalse(self.spatial.p07_report["changed"])
        self.assertEqual(
            self.spatial.p07_report["reason"],
            "current_hire_replay_error:ValueError",
        )

    def test_install_is_idempotent(self):
        wrapped = p07_atomic.reconcile
        wrapped_install = p07_atomic.install_spatial_hooks
        install_current_hire_window(p07_atomic)
        self.assertIs(p07_atomic.reconcile, wrapped)
        self.assertIs(p07_atomic.install_spatial_hooks, wrapped_install)


if __name__ == "__main__":
    unittest.main()
