# SPDX-License-Identifier: Apache-2.0
"""Carrier-isolation gates contributed from SOL-KEYSTONE's subordinate review."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import uuid

import main as public_main
import titan_capillary as capillary_module
from titan_capillary import CapillaryTitanAgent
import titan_runtime
from titan_runtime import TitanAgent


LAB = Path(__file__).resolve().parent


def _certified_identity_stage(routes, **_kwargs):
    staged = deepcopy(dict(routes))
    return staged, {
        "changed": False,
        "certified": True,
        "reason": "carrier_isolation_fixture",
        "changed_routes": [],
        "changed_steps": {},
    }


def _candidate(*, compiler=_certified_identity_stage):
    candidate = CapillaryTitanAgent()
    candidate._capillary_configuration = {
        "maxMarketOrdersPerTurn": 10,
        "turnsPerDay": 24,
    }
    with patch.object(
        capillary_module,
        "compile_jit_expensive_seed_routes",
        side_effect=compiler,
    ):
        candidate._initialize()
    return candidate


def _load_entrypoint():
    name = f"_capillary_order_rail_entry_{uuid.uuid4().hex}"
    path = LAB / "capillary_main.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


class RouteBankIsolationTests(unittest.TestCase):
    def test_candidate_detaches_from_plain_shared_route_bank(self):
        plain = TitanAgent()
        plain._initialize()
        shared = plain.controller.R
        shared_snapshot = deepcopy(shared)

        candidate = _candidate()

        self.assertTrue(candidate._capillary_compile_report["certified"])
        self.assertTrue(candidate._capillary_route_detach_report["detached"])
        self.assertEqual(
            candidate._capillary_route_detach_report["reason"],
            "private_route_bank_bound",
        )
        self.assertIsNot(candidate.controller.R, shared)
        self.assertIs(candidate.spatial._crop_routes, candidate.controller.R)
        self.assertEqual(candidate.controller.R, shared_snapshot)
        self.assertEqual(plain.controller.R, shared_snapshot)

    def test_two_candidate_instances_own_distinct_route_banks(self):
        left = _candidate()
        right = _candidate()

        self.assertIsNot(left.controller.R, right.controller.R)
        self.assertIs(left.spatial._crop_routes, left.controller.R)
        self.assertIs(right.spatial._crop_routes, right.controller.R)
        self.assertEqual(left.controller.R, right.controller.R)

        route_name = next(iter(left.controller.R))
        right_snapshot = deepcopy(right.controller.R)
        left.controller.R[route_name][0].setdefault("market", []).append(["HIRE"])
        self.assertNotEqual(left.controller.R, right.controller.R)
        self.assertEqual(right.controller.R, right_snapshot)

    def test_compiler_failure_keeps_private_route_bank(self):
        plain = TitanAgent()
        plain._initialize()
        shared = plain.controller.R
        shared_snapshot = deepcopy(shared)

        def fail(_routes, **_kwargs):
            raise ValueError("malformed target quantity")

        candidate = _candidate(compiler=fail)

        self.assertEqual(
            candidate._capillary_compile_report,
            {
                "changed": False,
                "certified": False,
                "reason": "compiler_input_invalid",
                "error_type": "ValueError",
            },
        )
        self.assertTrue(candidate._capillary_route_detach_report["detached"])
        self.assertIsNot(candidate.controller.R, shared)
        self.assertIs(candidate.spatial._crop_routes, candidate.controller.R)
        self.assertEqual(plain.controller.R, shared_snapshot)


class EvaluatorIsolationTests(unittest.TestCase):
    def test_each_evaluator_load_owns_private_canonical_instance_state(self):
        left = _load_entrypoint()
        right = _load_entrypoint()
        left_canonical = left._canonical_module()
        right_canonical = right._canonical_module()

        self.assertIsNot(left_canonical, right_canonical)
        self.assertEqual(Path(left_canonical.__file__).resolve(), LAB / "main.py")
        self.assertEqual(Path(right_canonical.__file__).resolve(), LAB / "main.py")
        self.assertIsNone(left_canonical._INSTANCE)
        self.assertIsNone(right_canonical._INSTANCE)

        marker = object()
        left_canonical._INSTANCE = marker
        self.assertIs(left_canonical._INSTANCE, marker)
        self.assertIsNone(right_canonical._INSTANCE)
        self.assertFalse(
            any(
                value is left_canonical or value is right_canonical
                for value in sys.modules.values()
            )
        )

    def test_entrypoint_load_does_not_patch_live_main_or_runtime(self):
        main_factory = public_main._new_instance
        main_instance = public_main._INSTANCE
        runtime_base = titan_runtime.TitanAgent

        entrypoint = _load_entrypoint()

        self.assertIs(public_main._new_instance, main_factory)
        self.assertIs(public_main._INSTANCE, main_instance)
        self.assertIs(titan_runtime.TitanAgent, runtime_base)
        self.assertIsNot(entrypoint._canonical_module(), public_main)

    def test_private_factory_preserves_canonical_code_and_candidate_mro(self):
        entrypoint = _load_entrypoint()
        candidate_base = entrypoint._CANDIDATE_RUNTIME.CapillaryTitanAgent
        predecessor_base = candidate_base.__mro__[1]
        factory = entrypoint._factory_with_candidate_base(
            candidate_base,
            predecessor_base,
        )

        self.assertIs(factory.__code__, entrypoint._CANONICAL_NEW_INSTANCE.__code__)
        self.assertIs(titan_runtime.TitanAgent, predecessor_base)

        feature_data = json.loads((LAB / "TITAN-CONFIG.json").read_text())
        instance = entrypoint._canonical_module()._new_instance(
            LAB,
            dict(feature_data),
        )
        mro = type(instance).__mro__
        self.assertEqual(mro[0].__name__, "FinalPressureAgent")
        self.assertIs(mro[1], candidate_base)
        self.assertIs(mro[2], predecessor_base)
        self.assertIs(titan_runtime.TitanAgent, predecessor_base)


if __name__ == "__main__":
    unittest.main(verbosity=2)
