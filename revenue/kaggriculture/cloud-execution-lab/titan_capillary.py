# SPDX-License-Identifier: Apache-2.0
"""Experimental TITAN candidate with structurally compiled JIT seed routes.

This module is intentionally separate from ``titan_runtime.py``.  It does not
change the submitted/default agent.  Instantiate ``CapillaryTitanAgent`` only in
an explicit candidate panel.
"""
from __future__ import annotations

from copy import deepcopy

from jit_seed_staging import compile_jit_expensive_seed_routes
from titan_runtime import TitanAgent


class CapillaryTitanAgent(TitanAgent):
    """TITAN with first-day expensive seed prepayment redistributed JIT."""

    def __init__(self, features=None, *, fourth_quadrant_admission=None):
        super().__init__(
            features,
            fourth_quadrant_admission=fourth_quadrant_admission,
        )
        self._capillary_configuration = {}
        self._capillary_compile_report = {
            "changed": False,
            "certified": False,
            "reason": "not_initialized",
        }

    def _initialize(self):
        super()._initialize()
        if self.features.consumer != "frozen" or self.features.terminal_route:
            self._capillary_compile_report = {
                "changed": False,
                "certified": False,
                "reason": "requires_nonterminal_frozen_consumer",
            }
            return

        cfg = self._capillary_configuration
        max_orders = int(cfg.get("maxMarketOrdersPerTurn", 10))
        turns_per_day = int(cfg.get("turnsPerDay", 24))
        staged, report = compile_jit_expensive_seed_routes(
            self.controller.R,
            max_orders=max_orders,
            turns_per_day=turns_per_day,
        )
        self._capillary_compile_report = report
        if not report["certified"]:
            return

        # Detach this candidate from any class/shared route mapping.  The actor
        # surface and branch topology were checked exact by the compiler.
        self.controller.R = staged
        self.seed_budget = self.seed_budget.__class__(self.controller.R)
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
        self.diagnostics["capillary_route_compile"] = deepcopy(
            self._capillary_compile_report
        )
        return result

    __call__ = act
