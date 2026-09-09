# SPDX-License-Identifier: Apache-2.0
"""Lifecycle and canonical-carrier regressions for the Capillary candidate."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import capillary_main as candidate_entrypoint
import titan_capillary as capillary_module
from titan_capillary import CapillaryTitanAgent
from titan_runtime import TitanAgent
import titan_runtime


LAB = Path(__file__).resolve().parent
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


class CanonicalEntrypointParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.canonical = candidate_entrypoint._canonical_module()
        cls.feature_data = json.loads((LAB / "TITAN-CONFIG.json").read_text())

    def new_instance(self):
        return self.canonical._new_instance(LAB, dict(self.feature_data))

    def test_adapter_delegates_to_exact_canonical_main(self):
        self.assertEqual(
            Path(self.canonical.__file__).resolve(),
            (LAB / "main.py").resolve(),
        )
        self.assertTrue(callable(self.canonical._entrypoint_fallback))
        self.assertTrue(callable(self.canonical._record_entrypoint_deadline))
        self.assertTrue(hasattr(self.canonical, "_INSTANCE"))
        self.assertFalse(hasattr(candidate_entrypoint, "_INSTANCE"))

        sentinel = object()
        observation = {"step": 17}
        configuration = {"episodeSteps": 720}
        with patch.object(self.canonical, "agent", return_value=sentinel) as delegated:
            result = candidate_entrypoint.agent(observation, configuration)

        self.assertIs(result, sentinel)
        delegated.assert_called_once_with(observation, configuration)

    def test_factory_preserves_final_pressure_over_capillary_mro(self):
        original_runtime_base = titan_runtime.TitanAgent
        instance = self.new_instance()

        self.assertIs(titan_runtime.TitanAgent, original_runtime_base)
        self.assertIsInstance(instance, CapillaryTitanAgent)
        mro = type(instance).__mro__
        self.assertEqual(mro[0].__name__, "FinalPressureAgent")
        self.assertIs(mro[1], CapillaryTitanAgent)
        self.assertIs(mro[2], original_runtime_base)
        self.assertTrue(instance.features.market_pressure)
        self.assertTrue(instance.features.early_capital)

    def test_final_pressure_is_suppressed_then_runs_once_after_capillary(self):
        instance = self.new_instance()
        instance.diagnostics = {"status": "completed"}
        before = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["BUY_LAND"], ["SELL", "WOOL", 1]],
        }
        after_capillary = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "WOOL", 1], ["BUY_LAND"]],
        }
        events = []

        def fake_capillary(_self, _obs, _cfg, selected):
            events.append(("capillary", selected))
            return after_capillary

        def fake_pressure(_self, _obs, _cfg, selected):
            self.assertTrue(_self._final_pressure_boundary)
            events.append(("pressure", selected))
            return selected

        with patch.object(
            CapillaryTitanAgent,
            "_early_capital_selected",
            new=fake_capillary,
        ), patch.object(
            TitanAgent,
            "_market_pressure_selected",
            new=fake_pressure,
        ):
            # Canonical FinalPressureAgent suppresses the earlier in-pipeline
            # call. No legacy pressure transform may run before Capillary.
            early = instance._market_pressure_selected({}, {}, before)
            self.assertIs(early, before)
            self.assertEqual(events, [])

            result = instance._early_capital_selected({}, {}, before)

        self.assertIs(result, after_capillary)
        self.assertEqual([event[0] for event in events], ["capillary", "pressure"])
        self.assertIs(events[0][1], before)
        self.assertIs(events[1][1], after_capillary)
        self.assertFalse(getattr(instance, "_final_pressure_boundary", False))

    def test_deadline_fallback_does_not_start_optional_final_pressure(self):
        instance = self.new_instance()
        instance.diagnostics = {"status": "deadline_fallback"}
        selected = object()
        after_capillary = object()
        calls = []

        def fake_capillary(_self, _obs, _cfg, _row):
            calls.append("capillary")
            return after_capillary

        def fake_pressure(_self, _obs, _cfg, _row):
            calls.append("pressure")
            return object()

        with patch.object(
            CapillaryTitanAgent,
            "_early_capital_selected",
            new=fake_capillary,
        ), patch.object(
            TitanAgent,
            "_market_pressure_selected",
            new=fake_pressure,
        ):
            result = instance._early_capital_selected({}, {}, selected)

        self.assertIs(result, after_capillary)
        self.assertEqual(calls, ["capillary"])


if __name__ == "__main__":
    unittest.main()
