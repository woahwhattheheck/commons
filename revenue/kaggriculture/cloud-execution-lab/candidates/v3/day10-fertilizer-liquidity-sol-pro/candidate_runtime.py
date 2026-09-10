# SPDX-License-Identifier: Apache-2.0
"""Install the fertilizer-liquidity arm at TITAN's final market boundary."""
from __future__ import annotations

from copy import deepcopy
from types import MethodType
from typing import Any, Callable

from fertilizer_liquidity import (
    ITEM,
    LiquiditySettings,
    executable_market_limit,
    propose_fertilizer_liquidity,
)

_MARKER = "_titan_day10_fertilizer_liquidity_installed"
_SAFE_UNCHANGED_GUARD_REASONS = frozenset({"sale_already_leaves_required_stock"})


def _active_fertilizer_sale(action: Any, configuration: Any) -> int:
    try:
        market = action.get("market") or []
        limit = executable_market_limit(configuration or {})
        return sum(
            int(row[2])
            for row in market[:limit]
            if isinstance(row, list)
            and len(row) == 3
            and row[:2] == ["SELL", ITEM]
            and type(row[2]) is int
            and row[2] > 0
        )
    except (AttributeError, TypeError, ValueError, IndexError, OverflowError):
        return 0


def install_final_boundary(
    instance: Any,
    *,
    post_units: Callable[[Any, Any, Any], tuple[Any, Any]],
    quote: Callable[[str, int, Any], Any],
    settings: LiquiditySettings = LiquiditySettings(),
) -> Any:
    """Wrap one runtime instance without patching the public runtime class.

    The canonical local ``FinalPressureAgent`` already owns the final
    ``_early_capital_selected`` seam.  This wrapper invokes it once, proposes a
    sale, binds an exact post-unit snapshot, and reruns the existing operating
    stock certificate.  An invented sale survives only when that certificate
    either withholds the required units or proves the proposed lot already
    leaves all certified productive obligations.
    """

    if getattr(instance, _MARKER, False):
        return instance
    original = instance._early_capital_selected

    def final_boundary(self: Any, observation: Any, configuration: Any, selected: Any) -> Any:
        returned = original(observation, configuration, selected)
        diagnostics = getattr(self, "diagnostics", None)
        if not isinstance(diagnostics, dict):
            return returned
        if diagnostics.get("status") != "completed":
            diagnostics["day10_fertilizer_liquidity"] = {
                "changed": False,
                "reason": "completed_action_required",
            }
            return returned

        consumer = getattr(self, "consumer", None)
        if consumer is None or not hasattr(self, "_operating_stock_selected"):
            diagnostics["day10_fertilizer_liquidity"] = {
                "changed": False,
                "reason": "operating_stock_certificate_unavailable",
            }
            return returned

        old_pair = getattr(consumer, "selected_post_units", None)
        old_binding = getattr(consumer, "selected_post_units_binding", None)
        installed_snapshot = False
        try:
            farm, private = post_units(observation, returned, configuration or {})
            if not isinstance(private, dict):
                raise ValueError("malformed_post_unit_private")
            shed = private.get("shed")
            if not isinstance(shed, dict):
                raise ValueError("malformed_post_unit_shed")
            stock = shed.get(ITEM)
            market = observation.get("market") if isinstance(observation, dict) else None
            params = market.get("params") if isinstance(market, dict) else None

            proposed, report = propose_fertilizer_liquidity(
                observation,
                configuration or {},
                returned,
                post_unit_fertilizer=stock,
                quote=lambda inventory: quote(ITEM, inventory, params),
                settings=settings,
            )
            if not report.get("changed"):
                diagnostics["day10_fertilizer_liquidity"] = report
                return returned

            step = int(observation["step"])
            player = int(observation["player"])
            farmer = deepcopy(proposed.get("farmer"))
            hands = deepcopy(proposed.get("hands", []))
            consumer.selected_post_units = (farm, private)
            consumer.selected_post_units_binding = (step, player, farmer, hands)
            installed_snapshot = True

            guarded = self._operating_stock_selected(
                observation, configuration or {}, proposed
            )
            guard_report = deepcopy(diagnostics.get("operating_stock") or {})
            guard_reason = guard_report.get("reason")
            certified = bool(guard_report.get("changed")) or (
                guard_reason in _SAFE_UNCHANGED_GUARD_REASONS
            )
            final_quantity = _active_fertilizer_sale(guarded, configuration)
            if not certified or final_quantity <= 0:
                consumer.selected_post_units = old_pair
                consumer.selected_post_units_binding = old_binding
                installed_snapshot = False
                report.update(
                    changed=False,
                    reason=(
                        "operating_stock_fully_reserved"
                        if certified
                        else f"operating_stock_not_certified:{guard_reason or 'missing_report'}"
                    ),
                    proposed_quantity=report.get("quantity", 0),
                    final_quantity=0,
                    operating_stock=guard_report,
                )
                diagnostics["day10_fertilizer_liquidity"] = report
                return returned

            report.update(
                changed=True,
                reason="certified_fertilizer_liquidity_sale",
                proposed_quantity=report.get("quantity", 0),
                final_quantity=final_quantity,
                operating_stock=guard_report,
                post_unit_snapshot_bound=True,
            )
            diagnostics["day10_fertilizer_liquidity"] = report
            return guarded
        except BaseException as error:
            # DeadlineExceeded inherits BaseException in the exact runtime.  Do
            # not consume it: restore this wrapper's temporary state and let the
            # canonical outer deadline handler own fallback.
            if installed_snapshot:
                consumer.selected_post_units = old_pair
                consumer.selected_post_units_binding = old_binding
            if error.__class__.__name__ == "DeadlineExceeded":
                raise
            diagnostics["day10_fertilizer_liquidity"] = {
                "changed": False,
                "reason": f"fail_closed:{type(error).__name__}:{error}",
            }
            return returned

    instance._early_capital_selected = MethodType(final_boundary, instance)
    setattr(instance, _MARKER, True)
    return instance
