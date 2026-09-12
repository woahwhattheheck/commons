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


class V219RetrySafeTests(unittest.TestCase):
    def test_identical_step433_retry_replays_initial_transaction_without_consuming_pending(self):
        route = helpers.route()
        digest = helpers.route_sha(route)
        obs = helpers.observation()
        parent = helpers.selected()
        first_action, first_state, first_report = safe.apply(
            obs,
            parent,
            helpers.CFG,
            enabled=True,
            route_snapshot=route,
            route_sha256=digest,
            state=safe.new_state(),
        )
        self.assertTrue(first_report["applied"])
        self.assertIsNotNone(first_state["pending"])
        pending = copy.deepcopy(first_state["pending"])

        replay_action, replay_state, replay_report = safe.apply(
            copy.deepcopy(obs),
            copy.deepcopy(parent),
            copy.deepcopy(helpers.CFG),
            enabled=True,
            route_snapshot=copy.deepcopy(route),
            route_sha256=digest,
            state=first_state,
        )
        self.assertEqual(replay_action, first_action)
        self.assertEqual(replay_state, first_state)
        self.assertEqual(replay_state["pending"], pending)
        self.assertEqual(replay_report["reason"], "same-step-replay")
        self.assertTrue(replay_report["replayed"])

    def test_conflicting_same_step_selected_action_fails_closed_and_preserves_state(self):
        route = helpers.route()
        digest = helpers.route_sha(route)
        obs = helpers.observation()
        first_action, first_state, _ = safe.apply(
            obs,
            helpers.selected(),
            helpers.CFG,
            enabled=True,
            route_snapshot=route,
            route_sha256=digest,
            state=safe.new_state(),
        )
        self.assertNotEqual(first_action, helpers.selected())
        conflict = helpers.selected(market=[["SELL", "WHEAT", 1]])
        action, later, report = safe.apply(
            obs,
            conflict,
            helpers.CFG,
            enabled=True,
            route_snapshot=route,
            route_sha256=digest,
            state=first_state,
        )
        self.assertEqual(action, conflict)
        self.assertEqual(later, first_state)
        self.assertEqual(report["reason"], "same-step-conflict")
        self.assertFalse(report["replayed"])

    def test_next_step_consumes_pending_once_and_then_replays_worker_result(self):
        route = helpers.route()
        digest = helpers.route_sha(route)
        _first_action, state, _ = safe.apply(
            helpers.observation(),
            helpers.selected(),
            helpers.CFG,
            enabled=True,
            route_snapshot=route,
            route_sha256=digest,
            state=safe.new_state(),
        )
        obs = helpers.observation(434, hands=2, unlocked=["NW", "NE", "SW", "SE"])
        obs["private"]["seeds"]["TOMATO"] = 10
        for y in (5, 6):
            for x in range(5, 10):
                obs["farms"][0]["tiles"][y][x] = None
        parent = helpers.selected(hands=2)
        action, later, report = safe.apply(
            obs,
            parent,
            helpers.CFG,
            enabled=True,
            route_snapshot=route,
            route_sha256=digest,
            state=state,
        )
        self.assertEqual(report["confirmed_workers"], 2)
        self.assertIsNone(later.get("pending"))

        replay_action, replay_state, replay_report = safe.apply(
            copy.deepcopy(obs),
            copy.deepcopy(parent),
            copy.deepcopy(helpers.CFG),
            enabled=True,
            route_snapshot=copy.deepcopy(route),
            route_sha256=digest,
            state=later,
        )
        self.assertEqual(replay_action, action)
        self.assertEqual(replay_state, later)
        self.assertEqual(replay_report["reason"], "same-step-replay")

    def test_same_step_enablement_change_cannot_replay_prior_enabled_action(self):
        route = helpers.route()
        digest = helpers.route_sha(route)
        obs = helpers.observation()
        _action, state, _ = safe.apply(
            obs,
            helpers.selected(),
            helpers.CFG,
            enabled=True,
            route_snapshot=route,
            route_sha256=digest,
            state=safe.new_state(),
        )
        action, later, report = safe.apply(
            obs,
            helpers.selected(),
            helpers.CFG,
            enabled=False,
            route_snapshot=route,
            route_sha256=digest,
            state=state,
        )
        self.assertEqual(action, helpers.selected())
        self.assertEqual(later, state)
        self.assertEqual(report["reason"], "same-step-conflict")


if __name__ == "__main__":
    unittest.main()
