# SPDX-License-Identifier: Apache-2.0
"""Install operating-stock at the current action's last stable market boundary."""
from __future__ import annotations

from functools import wraps
from types import MethodType
from typing import Any

from active_prefix import protect_final_current_prefix

INSTALL_MARKER = "__titan_v3_operating_stock_final_prefix__"


def install_final_boundary(instance: Any, operating_stock_module: Any):
    """Defer one instance's stock guard until after late market transforms.

    Canonical ``act`` calls ``_operating_stock_selected`` before crop release,
    then the completed-path finalizer calls ``_early_capital_selected``.  The
    canonical ``FinalPressureAgent`` implementation uses that latter method as
    the stable early-capital + final-pressure boundary.  This installer:

    * makes only the earlier stock hook a no-op;
    * calls the unchanged late hook first;
    * invokes the captured incumbent stock method exactly once afterward, with
      only the now-final current market prefix isolated; and
    * leaves deadline-fallback finalization unchanged.

    A fresh runtime instance is patched independently, so reconstruction cannot
    silently lose the candidate.
    """
    if getattr(instance, INSTALL_MARKER, False):
        return instance
    original_operating = getattr(instance, "_operating_stock_selected", None)
    original_late = getattr(instance, "_early_capital_selected", None)
    original_guard = getattr(operating_stock_module, "protect_operating_stock", None)
    if not all(callable(item) for item in (original_operating, original_late, original_guard)):
        raise ValueError("missing_operating_stock_boundary")

    @wraps(original_operating)
    def deferred(self, obs, cfg, selected):
        diagnostics = getattr(self, "diagnostics", None)
        if isinstance(diagnostics, dict):
            diagnostics["operating_stock"] = {
                "changed": False,
                "reason": "deferred_to_final_completed_boundary",
                "deferred": True,
            }
        return selected

    @wraps(original_late)
    def final_boundary(self, obs, cfg, selected):
        returned = original_late(obs, cfg, selected)
        diagnostics = getattr(self, "diagnostics", None)
        # Canonical fallback never re-runs operating-stock in _finish_production.
        # Preserve that action behavior exactly; only completed actions enter the
        # candidate's final boundary.
        if not isinstance(diagnostics, dict) or diagnostics.get("status") != "completed":
            return returned

        previous_guard = operating_stock_module.protect_operating_stock

        @wraps(original_guard)
        def final_prefix_guard(mechanics, observation, configuration, action,
                               post_farm, post_private, route, checkpoints=()):
            return protect_final_current_prefix(
                original_guard,
                mechanics,
                observation,
                configuration,
                action,
                post_farm,
                post_private,
                route,
                checkpoints,
            )

        operating_stock_module.protect_operating_stock = final_prefix_guard
        try:
            return original_operating(obs, cfg, returned)
        finally:
            operating_stock_module.protect_operating_stock = previous_guard

    instance._operating_stock_selected = MethodType(deferred, instance)
    instance._early_capital_selected = MethodType(final_boundary, instance)
    setattr(instance, INSTALL_MARKER, {
        "original_operating": original_operating,
        "original_late": original_late,
        "original_guard": original_guard,
    })
    return instance
