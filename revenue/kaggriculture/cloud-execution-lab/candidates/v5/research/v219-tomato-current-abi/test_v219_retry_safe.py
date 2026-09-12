# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"unable to load {name}")
    spec.loader.exec_module(module)
    return module


helpers = _load("v219_contract_helpers", HERE / "test_v219_current.py")
safe = _load("v219_current_safe", HERE / "v219_current_safe.py")


class Controller:
    def __init__(self, routes, cur="A"):
        self.R = routes
        self.cur = cur


def controller_for(route_a=None, route_b=None, *, cur="A"):
    route_a = helpers.route() if route_a is None else route_a
    route_b = helpers.route() if route_b is None else route_b
    return Controller({"A": route_a, "B": route_b}, cur=cur)


def run_safe(obs, parent, state, controller, route_id="A", *, enabled=True, cfg=None):
    return safe.apply(
        obs,
        parent,
        helpers.CFG if cfg is None else cfg,
        enabled=enabled,
        controller=controller,
        completed_route_id=route_id,
        state=state,
    )


class V219RetrySafeTests(unittest.TestCase):
    def test_identical_step433_retry_replays_initial_transaction_without_consuming_pending(self):
        ctl = controller_for()
        obs = helpers.observation()
        parent = helpers.selected()
        first_action, first_state, first_report = run_safe(
            obs, parent, safe.new_state(), ctl)
        self.assertTrue(first_report["applied"])
        self.assertEqual(first_report["committed_route_id"], "A")
        self.assertIsNotNone(first_state["pending"])
        pending = copy.deepcopy(first_state["pending"])

        replay_action, replay_state, replay_report = run_safe(
            copy.deepcopy(obs), copy.deepcopy(parent), first_state, ctl)
        self.assertEqual(replay_action, first_action)
        self.assertEqual(replay_state, first_state)
        self.assertEqual(replay_state["pending"], pending)
        self.assertEqual(replay_report["reason"], "same-step-replay")
        self.assertTrue(replay_report["replayed"])

    def test_conflicting_same_step_selected_action_fails_closed_and_preserves_state(self):
        ctl = controller_for()
        obs = helpers.observation()
        first_action, first_state, _ = run_safe(
            obs, helpers.selected(), safe.new_state(), ctl)
        self.assertNotEqual(first_action, helpers.selected())
        conflict = helpers.selected(market=[["SELL", "WHEAT", 1]])
        action, later, report = run_safe(obs, conflict, first_state, ctl)
        self.assertEqual(action, conflict)
        self.assertEqual(later, first_state)
        self.assertEqual(report["reason"], "same-step-conflict")
        self.assertFalse(report["replayed"])

    def test_next_step_consumes_pending_once_and_then_replays_worker_result(self):
        ctl = controller_for()
        _first_action, state, _ = run_safe(
            helpers.observation(), helpers.selected(), safe.new_state(), ctl)
        obs = helpers.observation(434, hands=2, unlocked=["NW", "NE", "SW", "SE"])
        obs["private"]["seeds"]["TOMATO"] = 10
        for y in (5, 6):
            for x in range(5, 10):
                obs["farms"][0]["tiles"][y][x] = None
        parent = helpers.selected(hands=2)
        action, later, report = run_safe(obs, parent, state, ctl)
        self.assertEqual(report["confirmed_workers"], 2)
        self.assertIsNone(later.get("pending"))

        replay_action, replay_state, replay_report = run_safe(
            copy.deepcopy(obs), copy.deepcopy(parent), later, ctl)
        self.assertEqual(replay_action, action)
        self.assertEqual(replay_state, later)
        self.assertEqual(replay_report["reason"], "same-step-replay")

    def test_enablement_change_never_replays_prior_enabled_action(self):
        ctl = controller_for()
        obs = helpers.observation()
        _action, state, _ = run_safe(
            obs, helpers.selected(), safe.new_state(), ctl)
        action, later, report = run_safe(
            obs, helpers.selected(), state, ctl, enabled=False)
        self.assertEqual(action, helpers.selected())
        self.assertEqual(later, state)
        self.assertEqual(report["reason"], "disabled")

    def test_committed_route_id_beats_raw_cur(self):
        route_a = helpers.route()
        route_b = helpers.route()
        route_b[500]["market"] = [["BUY_LAND"]]
        ctl = controller_for(route_a, route_b, cur="B")

        action_a, state_a, report_a = run_safe(
            helpers.observation(), helpers.selected(), safe.new_state(), ctl, route_id="A")
        self.assertTrue(state_a["eligible"])
        self.assertTrue(report_a["applied"])
        self.assertIn(["BUY_LAND"], action_a["market"])

        action_b, state_b, report_b = run_safe(
            helpers.observation(), helpers.selected(), safe.new_state(), ctl, route_id="B")
        self.assertFalse(state_b["eligible"])
        self.assertEqual(action_b, helpers.selected())
        self.assertEqual(report_b["reason"], "not-eligible")

    def test_missing_or_unknown_committed_route_fails_closed(self):
        ctl = controller_for(cur="B")
        for route_id in (None, "", "MISSING"):
            with self.subTest(route_id=route_id):
                parent = helpers.selected()
                state = safe.new_state()
                action, later, report = run_safe(
                    helpers.observation(), parent, state, ctl, route_id=route_id)
                self.assertEqual(action, parent)
                self.assertEqual(later, state)
                self.assertEqual(report["reason"], "route-authority")

    def test_changed_committed_route_same_step_cannot_hit_retry_cache(self):
        route_a = helpers.route()
        ctl = controller_for(route_a, helpers.route())
        obs = helpers.observation()
        parent = helpers.selected()
        first_action, first_state, _ = run_safe(
            obs, parent, safe.new_state(), ctl)
        self.assertNotEqual(first_action, parent)

        changed = copy.deepcopy(route_a)
        changed[500]["market"] = [["SELL", "WHEAT", 1]]
        ctl.R["A"] = changed
        action, later, report = run_safe(obs, parent, first_state, ctl)
        self.assertEqual(action, parent)
        self.assertEqual(later, first_state)
        self.assertEqual(report["reason"], "same-step-conflict")

    def test_missing_required_config_key_fails_closed(self):
        ctl = controller_for()
        for missing in helpers.CFG:
            with self.subTest(missing=missing):
                cfg = dict(helpers.CFG)
                del cfg[missing]
                parent = helpers.selected()
                state = safe.new_state()
                action, later, report = run_safe(
                    helpers.observation(), parent, state, ctl, cfg=cfg)
                self.assertEqual(action, parent)
                self.assertEqual(later, state)
                self.assertEqual(report["reason"], "unsupported-config")

    def test_public_adapter_exposes_no_injected_route_snapshot_or_sha_parameters(self):
        import inspect
        params = inspect.signature(safe.apply).parameters
        self.assertNotIn("route_snapshot", params)
        self.assertNotIn("route_sha256", params)
        self.assertIn("controller", params)
        self.assertIn("completed_route_id", params)


if __name__ == "__main__":
    unittest.main()
