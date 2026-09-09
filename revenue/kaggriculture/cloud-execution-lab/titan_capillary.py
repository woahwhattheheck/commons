# SPDX-License-Identifier: Apache-2.0
"""Executable TITAN Capillary candidate with order-preserving JIT seed routes.

This module is isolated from ``titan_runtime.py`` and the submitted/default
agent. It detaches the inherited shared route bank without mutating it, binds
SpatialTempo to the private route object, and compiles only order-preserving
JIT seed placements. Use ``capillary_main.agent`` for canonical final-pressure,
deadline, reset, and fallback composition.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from jit_seed_order_rail import compile_jit_expensive_seed_routes
from titan_runtime import TitanAgent


class CapillaryTitanAgent(TitanAgent):
    """TITAN base with day-zero expensive seed prepayment redistributed JIT."""

    def __init__(self, features=None, *, fourth_quadrant_admission=None):
        super().__init__(
            features,
            fourth_quadrant_admission=fourth_quadrant_admission,
        )
        self._capillary_configuration = {}
        self._capillary_route_detach_report = {
            "detached": False,
            "reason": "not_initialized",
        }
        self._capillary_compile_report = {
            "changed": False,
            "certified": False,
            "reason": "not_initialized",
        }

    @staticmethod
    def _closure_bindings(function: Any) -> dict[str, Any] | None:
        code = getattr(function, "__code__", None)
        closure = getattr(function, "__closure__", None)
        if code is None or closure is None or len(code.co_freevars) != len(closure):
            return None
        bindings: dict[str, Any] = {}
        try:
            for name, cell in zip(code.co_freevars, closure):
                bindings[name] = cell.cell_contents
        except ValueError:
            return None
        return bindings

    def _detach_spatial_route_bank(self) -> bool:
        """Unwrap one verified SpatialTempo layer, detach, then reinstall once."""
        source = self.controller.R
        if not isinstance(source, dict):
            self._capillary_route_detach_report = {
                "detached": False,
                "reason": "controller_routes_not_dict",
            }
            return False

        if self.spatial is None:
            self.controller.R = deepcopy(source)
            self._capillary_route_detach_report = {
                "detached": True,
                "reason": "detached_without_spatial_wrapper",
                "route_count": len(self.controller.R),
            }
            return True

        wrapped = self.controller.act
        bindings = self._closure_bindings(wrapped)
        if (
            bindings is None
            or bindings.get("self") is not self.spatial
            or bindings.get("controller") is not self.controller
            or bindings.get("pristine") is not source
            or not callable(bindings.get("original"))
            or getattr(self.spatial, "_crop_routes", None) is not source
        ):
            self._capillary_route_detach_report = {
                "detached": False,
                "reason": "spatial_wrapper_binding_unrecognized",
                "freevars": [] if bindings is None else sorted(bindings),
            }
            return False

        original = bindings["original"]
        previous_crop_routes = self.spatial._crop_routes
        try:
            private_routes = deepcopy(source)
            # Remove exactly the verified SpatialTempo layer. Any earlier
            # quadrant/controller wrapper remains inside ``original``.
            self.controller.act = original
            self.controller.R = private_routes
            self.spatial.install(self.controller)
            rebound = self._closure_bindings(self.controller.act)
            if (
                self.spatial._crop_routes is not private_routes
                or rebound is None
                or rebound.get("self") is not self.spatial
                or rebound.get("controller") is not self.controller
                or rebound.get("pristine") is not private_routes
                or rebound.get("original") is not original
            ):
                raise RuntimeError("spatial reinstall did not bind private routes")
        except Exception as error:
            self.controller.R = source
            self.controller.act = wrapped
            self.spatial._crop_routes = previous_crop_routes
            self._capillary_route_detach_report = {
                "detached": False,
                "reason": "spatial_rebind_failed",
                "error_type": type(error).__name__,
            }
            return False

        self._capillary_route_detach_report = {
            "detached": True,
            "reason": "private_route_bank_bound",
            "route_count": len(private_routes),
            "source_identity_preserved": source is not private_routes,
        }
        return True

    def _initialize(self):
        super()._initialize()
        if self.features.consumer != "frozen" or self.features.terminal_route:
            self._capillary_compile_report = {
                "changed": False,
                "certified": False,
                "reason": "requires_nonterminal_frozen_consumer",
            }
            return

        if not self._detach_spatial_route_bank():
            self._capillary_compile_report = {
                "changed": False,
                "certified": False,
                "reason": "route_detach_failed",
            }
            return

        # The predecessor SeedBudget was constructed over the shared route bank.
        # Rebuild it before compilation and again after staged bytes are applied.
        self.seed_budget = self.seed_budget.__class__(self.controller.R)
        self._seed_plan = None

        cfg = self._capillary_configuration
        max_orders = int(cfg.get("maxMarketOrdersPerTurn", 10))
        turns_per_day = int(cfg.get("turnsPerDay", 24))
        try:
            staged, report = compile_jit_expensive_seed_routes(
                self.controller.R,
                max_orders=max_orders,
                turns_per_day=turns_per_day,
            )
        except Exception as error:
            self._capillary_compile_report = {
                "changed": False,
                "certified": False,
                "reason": "compiler_input_invalid",
                "error_type": type(error).__name__,
            }
            return
        self._capillary_compile_report = report
        if not report.get("certified"):
            if self.spatial is not None:
                self.spatial.seed_reserve = (
                    lambda crop, step, current:
                    self.seed_budget.remaining(crop, step, current)
                )
            return

        routes = self.controller.R
        if self.spatial is not None and self.spatial._crop_routes is not routes:
            self._capillary_compile_report = {
                **report,
                "changed": False,
                "certified": False,
                "reason": "spatial_route_binding_mismatch",
            }
            return
        routes.clear()
        routes.update(staged)
        self.seed_budget = self.seed_budget.__class__(routes)
        self._seed_plan = None
        if self.spatial is not None:
            self.spatial.seed_reserve = (
                lambda crop, step, current:
                self.seed_budget.remaining(crop, step, current)
            )

    def act(self, observation, configuration=None, *, entry_started=None):
        self._capillary_configuration = dict(configuration or {})
        result = super().act(
            observation,
            configuration,
            entry_started=entry_started,
        )
        self.diagnostics["capillary_route_detach"] = deepcopy(
            self._capillary_route_detach_report
        )
        self.diagnostics["capillary_route_compile"] = deepcopy(
            self._capillary_compile_report
        )
        return result

    __call__ = act
