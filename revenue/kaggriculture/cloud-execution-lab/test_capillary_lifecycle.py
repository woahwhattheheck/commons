# SPDX-License-Identifier: Apache-2.0
"""Lifecycle and canonical-carrier regressions for the Capillary candidate."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

import capillary_main as candidate_entrypoint
import titan_capillary as capillary_module
from titan_capillary import CapillaryTitanAgent
from titan_runtime import Features, TitanAgent


_MARKER = ["BUY_SEED", "MELON", 1]


class _StopBeforeControllerAct(RuntimeError):
    """Interrupt the installed SpatialTempo wrapper after route publication."""


def _certified_stage(routes, **_kwargs):
    staged = deepcopy(dict(routes))
    route_name = next(iter(staged))
    route = list(staged[route_name])
    action = deepcopy(route[0])
    action["market"] = list(action.get("market", [])) + [list(_MARKER)]
    route[0] = action
    staged[route_name] = route
    return staged, {
        "changed": True,
        "certified": True,
        "reason": "staged",
        "changed_routes": [str(route_name)],
        "changed_steps": {str(route_name): [0]},
    }


def _has_marker(routes):
    return any(
        order == _MARKER
        for route in routes.values()
        for action in route
        for order in action.get("market", [])
    )


class CapillaryLifecycleTests(unittest.TestCase):
    def _candidate(self):
        agent = CapillaryTitanAgent()
        agent._capillary_configuration = {
            "maxMarketOrdersPerTurn": 10,
            "turnsPerDay": 24,
        }
        with patch.object(
            capillary_module,
            "compile_jit_expensive_seed_routes",
            side_effect=_certified_stage,
        ):
            agent._initialize()
        self.assertTrue(agent._capillary_compile_report["certified"])
        self.assertTrue(_has_marker(agent.controller.R))
        return agent

    def test_spatial_wrapper_captures_the_staged_route_object(self):
        agent = self._candidate()
        staged = deepcopy(agent.controller.R)

        # SpatialTempo.install() executes before Capillary's compiler. Its
        # private route reference and wrapper closure must nevertheless remain
        # bound to the same object that now contains the staged bytes.
        self.assertIs(agent.spatial._crop_routes, agent.controller.R)

        captured = {}

        def stop_after_publication(controller, pristine, observation):
            captured["controller"] = controller
            captured["pristine"] = pristine
            captured["observation"] = observation
            raise _StopBeforeControllerAct

        agent.spatial._begin = stop_after_publication
        marker = object()
        with self.assertRaises(_StopBeforeControllerAct):
            agent.controller.act(marker)

        self.assertIs(captured["controller"], agent.controller)
        self.assertIs(captured["pristine"], agent.controller.R)
        self.assertIs(captured["observation"], marker)
        self.assertEqual(captured["pristine"], staged)

    def test_reconstruction_rebinds_without_cross_instance_mutation(self):
        plain = TitanAgent()
        plain._initialize()
        plain_routes = plain.controller.R
        plain_snapshot = deepcopy(plain_routes)

        agent = self._candidate()
        first_routes = agent.controller.R
        staged_snapshot = deepcopy(first_routes)

        self.assertIsNot(first_routes, plain_routes)
        self.assertNotEqual(staged_snapshot, plain_snapshot)
        self.assertEqual(plain.controller.R, plain_snapshot)

        # Deadline recovery constructs a fresh controller while retaining the
        # SpatialTempo object. The new installation must capture the new
        # per-instance map, and the compiler must preserve that new identity.
        agent.ready = False
        with patch.object(
            capillary_module,
            "compile_jit_expensive_seed_routes",
            side_effect=_certified_stage,
        ):
            agent._initialize()

        self.assertTrue(agent._capillary_compile_report["certified"])
        self.assertIsNot(agent.controller.R, first_routes)
        self.assertIs(agent.spatial._crop_routes, agent.controller.R)
        self.assertEqual(agent.controller.R, staged_snapshot)
        self.assertEqual(plain.controller.R, plain_snapshot)

    def test_expected_compiler_conversion_failure_is_runtime_fail_closed(self):
        agent = CapillaryTitanAgent()
        with patch.object(
            capillary_module,
            "compile_jit_expensive_seed_routes",
            side_effect=ValueError("malformed target quantity"),
        ):
            agent._initialize()

        self.assertEqual(
            agent._capillary_compile_report,
            {
                "changed": False,
                "certified": False,
                "reason": "compiler_input_invalid",
                "error_type": "ValueError",
            },
        )
        self.assertIs(agent.spatial._crop_routes, agent.controller.R)


class FinalPressureParityTests(unittest.TestCase):
    def test_direct_runtime_keeps_canonical_capital_then_pressure_order(self):
        agent = CapillaryTitanAgent(Features(market_pressure=True))
        agent.diagnostics = {"status": "completed"}
        selected = {"stage": "selected"}
        after_capital = {"stage": "capital"}
        after_pressure = {"stage": "pressure"}
        calls = []

        def early(_agent, obs, cfg, row):
            calls.append(("early", obs, cfg, row))
            return after_capital

        def pressure(_agent, obs, cfg, row):
            self.assertTrue(_agent._final_pressure_boundary)
            calls.append(("pressure", obs, cfg, row))
            return after_pressure

        obs, cfg = object(), object()
        with patch.object(TitanAgent, "_early_capital_selected", new=early), patch.object(
            TitanAgent,
            "_market_pressure_selected",
            new=pressure,
        ):
            # Pressure remains suppressed at its legacy earlier call site.
            self.assertIs(agent._market_pressure_selected(obs, cfg, selected), selected)
            self.assertEqual(calls, [])

            result = agent._early_capital_selected(obs, cfg, selected)

        self.assertIs(result, after_pressure)
        self.assertEqual(
            calls,
            [
                ("early", obs, cfg, selected),
                ("pressure", obs, cfg, after_capital),
            ],
        )
        self.assertFalse(agent._final_pressure_boundary)

    def test_deadline_fallback_does_not_start_optional_final_pressure(self):
        agent = CapillaryTitanAgent(Features(market_pressure=True))
        agent.diagnostics = {"status": "deadline_fallback"}
        selected = object()
        after_capital = object()
        calls = []

        def early(_agent, _obs, _cfg, _row):
            calls.append("early")
            return after_capital

        def pressure(_agent, _obs, _cfg, _row):
            calls.append("pressure")
            return object()

        with patch.object(TitanAgent, "_early_capital_selected", new=early), patch.object(
            TitanAgent,
            "_market_pressure_selected",
            new=pressure,
        ):
            result = agent._early_capital_selected(object(), object(), selected)

        self.assertIs(result, after_capital)
        self.assertEqual(calls, ["early"])


class CanonicalEntrypointParityTests(unittest.TestCase):
    def test_factory_changes_only_the_runtime_class(self):
        instance = candidate_entrypoint._new_instance(
            Path("."),
            {"market_pressure": True},
        )
        self.assertIsInstance(instance, CapillaryTitanAgent)
        self.assertTrue(instance.features.market_pressure)
        self.assertIs(
            candidate_entrypoint._CONTROL_MAIN._new_instance,
            candidate_entrypoint._new_instance,
        )

    def test_agent_delegates_to_exact_canonical_whole_call_guard(self):
        observation, configuration, returned = object(), object(), object()
        with patch.object(
            candidate_entrypoint._CONTROL_MAIN,
            "agent",
            return_value=returned,
        ) as delegated:
            result = candidate_entrypoint.agent(observation, configuration)

        self.assertIs(result, returned)
        delegated.assert_called_once_with(observation, configuration)


if __name__ == "__main__":
    unittest.main()
