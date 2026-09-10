# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from p07_atomic import (
    P07_KIND,
    install_agent,
    install_spatial_hooks,
    reconcile,
)
from spatial_tempo import SpatialTempo, set_unit, unit
from test_joint_assignment import crossing_fixture, row


class Controller:
    def __init__(self, route):
        self.cur = 0
        self.R = {0: route}


class P07AtomicIntegrationTests(unittest.TestCase):
    def setUp(self):
        mechanics, observation, route = crossing_fixture()
        while len(route) < 720:
            route.append(row())
        observation.update(step=0, day=0, hour=0)
        self.mechanics = mechanics
        self.observation = observation
        self.route = route
        self.controller = Controller(route)
        self.spatial = SpatialTempo(mechanics)
        self.spatial.configuration = {
            "turnsPerDay": 24,
            "episodeSteps": 720,
            "shedCapacity": 100,
        }
        self.instance = SimpleNamespace(
            spatial=self.spatial,
            quadrant=SimpleNamespace(active=False),
        )
        install_spatial_hooks(self.spatial, self.instance, enabled=True)
        self.selected = deepcopy(route[0])

    def propose(self):
        return reconcile(
            self.spatial,
            self.observation,
            deepcopy(self.selected),
            self.controller,
        )

    def stage_finish(self, selected):
        self.spatial._pending = {
            "previous": None,
            "events": list(self.spatial.events),
            "plans": dict(self.spatial.plans),
        }
        self.spatial._selected = deepcopy(selected)

    def p07_plans(self):
        state = self.spatial._committed or {}
        return {
            worker: plan
            for worker, plan in (state.get("plans") or {}).items()
            if plan.get("kind") == P07_KIND
        }

    def test_exact_predecessor_fixture_changes_both_current_and_future(self):
        original_route = deepcopy(self.route)
        output = self.propose()
        report = self.spatial.p07_report
        self.assertTrue(report["changed"], report)
        pair = tuple(report["pair"])
        self.assertEqual(len(pair), 2)
        self.assertTrue(
            any(unit(output, worker) != unit(self.selected, worker) for worker in pair)
        )
        changed_future = [
            step
            for step in range(1, report["end_step"] + 1)
            if any(
                unit(self.route[step], worker)
                != unit(original_route[step], worker)
                for worker in pair
            )
        ]
        self.assertTrue(changed_future)
        self.assertEqual(set(self.spatial.plans), set(pair))
        self.assertEqual(
            {_plan["owner"] for _plan in self.spatial.plans.values()},
            {report["owner"]},
        )

    def test_later_one_sided_rewrite_rolls_back_both_current_actions(self):
        output = self.propose()
        pending = self.spatial._p07_pending
        pair = tuple(pending["pair"])
        one_sided = deepcopy(output)
        set_unit(
            one_sided,
            pair[1],
            list(pending["baseline_current"][pair[1]]),
        )
        guarded = self.spatial.guard_returned(self.observation, one_sided)
        for worker in pair:
            self.assertEqual(
                unit(guarded, worker),
                pending["baseline_current"][worker],
            )
        self.assertEqual(
            self.spatial._p07_pending["guard_decision"], "rollback_pair"
        )

    def test_both_returned_actions_commit_both_continuations(self):
        output = self.propose()
        pending = deepcopy(self.spatial._p07_pending)
        self.stage_finish(output)
        guarded = self.spatial.guard_returned(self.observation, output)
        self.spatial.finish(self.observation, guarded)
        plans = self.p07_plans()
        self.assertEqual(set(plans), set(pending["pair"]))
        self.assertEqual(
            {plan["owner"] for plan in plans.values()}, {pending["owner"]}
        )
        self.assertTrue(self.spatial.p07_finish_report["committed"])
        self.assertFalse(self.spatial.p07_finish_report["atomic_repair"])

    def test_finish_backstop_erases_a_bypassed_half_commit(self):
        output = self.propose()
        pending = deepcopy(self.spatial._p07_pending)
        pair = tuple(pending["pair"])
        self.stage_finish(output)
        bypassed = deepcopy(output)
        set_unit(
            bypassed,
            pair[1],
            list(pending["baseline_current"][pair[1]]),
        )
        # Deliberately bypass guard_returned to exercise the second boundary.
        self.spatial.finish(self.observation, bypassed)
        self.assertEqual(self.p07_plans(), {})
        self.assertTrue(self.spatial.p07_finish_report["atomic_repair"])
        self.assertFalse(self.spatial.p07_finish_report["committed"])

    def test_current_route_mismatch_fails_closed_without_mutation(self):
        original_route = deepcopy(self.route)
        selected = deepcopy(self.selected)
        selected["farmer"] = ["PASS"]
        output = reconcile(
            self.spatial, self.observation, selected, self.controller
        )
        self.assertEqual(output, selected)
        self.assertEqual(self.route, original_route)
        self.assertFalse(self.spatial.p07_report["changed"])
        self.assertIn(
            self.spatial.p07_report["reason"],
            {
                "fewer_than_two_eligible_actors",
                "no_common_complete_bundle_horizon",
            },
        )

    def test_current_market_is_a_hard_boundary(self):
        original_route = deepcopy(self.route)
        selected = deepcopy(self.selected)
        selected["market"] = [["SELL", "WHEAT", 1]]
        output = reconcile(
            self.spatial, self.observation, selected, self.controller
        )
        self.assertEqual(output, selected)
        self.assertEqual(self.route, original_route)
        self.assertEqual(
            self.spatial.p07_report["reason"], "current_market_boundary"
        )

    def test_existing_actor_ownership_excludes_that_pair(self):
        self.spatial.plans[0] = {
            "kind": "other",
            "step": 0,
            "end": 5,
            "route": 0,
            "replacement": [["PASS"]],
        }
        self.spatial.active[0] = 5
        original = deepcopy(self.route)
        output = self.propose()
        self.assertEqual(output, self.selected)
        self.assertEqual(self.route, original)
        self.assertFalse(self.spatial.p07_report["changed"])
        self.assertEqual(
            self.spatial.p07_report["reason"],
            "fewer_than_two_eligible_actors",
        )

    def test_quadrant_owner_blocks_p07(self):
        self.instance.quadrant.active = {0: 10}
        original = deepcopy(self.route)
        result = reconcile(
            self.spatial,
            self.observation,
            deepcopy(self.selected),
            self.controller,
            owner_busy=True,
        )
        self.assertEqual(self.spatial.p07_report["reason"], "other_owner_active")
        self.assertEqual(result, self.selected)
        self.assertEqual(self.route, original)

    def test_every_noop_step_is_logged_not_only_hour_23(self):
        selected = deepcopy(self.selected)
        selected["market"] = [["SELL", "WHEAT", 1]]
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "trace.jsonl"
            old = os.environ.get("TITAN_P07_LOG")
            os.environ["TITAN_P07_LOG"] = str(log)
            try:
                reconcile(
                    self.spatial, self.observation, selected, self.controller
                )
            finally:
                if old is None:
                    os.environ.pop("TITAN_P07_LOG", None)
                else:
                    os.environ["TITAN_P07_LOG"] = old
            rows = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["step"], 0)
        self.assertEqual(rows[0]["phase"], "proposal")
        self.assertEqual(rows[0]["reason"], "current_market_boundary")

    def test_disabled_hook_preserves_direct_canonical_transform(self):
        mechanics, observation, route = crossing_fixture()
        while len(route) < 720:
            route.append(row())
        observation.update(step=0, day=0, hour=0)
        spatial = SpatialTempo(mechanics, pathing=False, tempo=False)
        spatial.configuration = {
            "turnsPerDay": 24,
            "episodeSteps": 720,
            "shedCapacity": 100,
        }
        controller = Controller(route)
        instance = SimpleNamespace(
            spatial=spatial, quadrant=SimpleNamespace(active=False)
        )
        install_spatial_hooks(spatial, instance, enabled=False)
        selected = deepcopy(route[0])
        before = deepcopy(route)
        output = spatial.transform(observation, selected, controller)
        self.assertEqual(output, selected)
        self.assertEqual(route, before)
        self.assertEqual(spatial.p07_report["reason"], "feature_disabled")

    def test_install_agent_reapplies_hooks_after_reconstruction(self):
        created = []

        class FakeSpatial:
            def __init__(self):
                self.configuration = {}
                self.transform = lambda obs, selected, controller: selected
                self.guard_returned = (
                    lambda observation, returned, repair_fallback=False: returned
                )
                self.finish = lambda observation, returned, post=None: None

        class FakeAgent:
            def __init__(self):
                self.spatial = None
                self.quadrant = SimpleNamespace(active=False)

            def _initialize(self):
                self.spatial = FakeSpatial()
                created.append(self.spatial)

        agent = FakeAgent()
        install_agent(agent, enabled=True)
        agent._initialize()
        agent._initialize()
        self.assertEqual(len(created), 2)
        self.assertTrue(all(item._p07_hooks_installed for item in created))
        self.assertTrue(all(item._p07_enabled for item in created))


if __name__ == "__main__":
    unittest.main()
