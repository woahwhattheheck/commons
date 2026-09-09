# SPDX-License-Identifier: Apache-2.0
"""Order-preserving admission wrapper for Capillary JIT seed staging.

The predecessor compiler can fill the first blank market slot on a target turn.
That preserves row indices but can still execute a staged seed purchase before an
inherited HIRE, LAND, product, or animal purchase.  Since market execution is
ordered and affordability is mutable, the earlier seed row can make an inherited
row lose its fill.

This module keeps the frozen predecessor compiler byte-exact and runs an isolated
clone whose placement primitive may only append below the active-order cap or
reuse a *trailing* active-prefix blank after every inherited nonblank row.  It
also validates every route row before any predecessor quantity conversion and
verifies the complete changed market surface after compilation.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
from types import FunctionType
from typing import Any, Mapping, Sequence

import jit_seed_staging as _base


EXPECTED_BASE_COMPILER_GIT_BLOB = "e1cf2485ab869cf3c6f5eec455b0a25f6aeaa505"
ORDER_RAIL_SCHEMA = 1
_QUANTITY_ORDERS = frozenset({"SELL", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL"})


def _git_blob_sha1(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def _base_blob() -> tuple[str | None, str | None]:
    try:
        data = Path(_base.__file__).read_bytes()
    except (OSError, TypeError) as error:
        return None, type(error).__name__
    return _git_blob_sha1(data), None


def _copy_routes(routes: Any) -> dict[Any, Any]:
    if not isinstance(routes, Mapping):
        return {}
    try:
        return deepcopy(dict(routes))
    except Exception:  # pragma: no cover - defensive around hostile Mapping objects.
        return {}


def _crop_labels(expensive_crops: Any) -> list[str]:
    if isinstance(expensive_crops, (str, bytes, bytearray)):
        return []
    try:
        return sorted({crop for crop in expensive_crops if type(crop) is str and crop})
    except TypeError:
        return []


def _failure_report(
    routes: Any,
    *,
    reason: str,
    max_orders: Any,
    turns_per_day: Any,
    expensive_crops: Any,
    first_day_only: Any,
    detail: Mapping[str, Any] | None = None,
    base_blob: str | None = None,
) -> tuple[dict[Any, Any], dict[str, Any]]:
    rejection = dict(detail or {})
    rejection.setdefault("reason", reason)
    return _copy_routes(routes), {
        "changed": False,
        "certified": False,
        "reason": reason,
        "max_orders": max_orders,
        "turns_per_day": turns_per_day,
        "first_day_only": first_day_only,
        "expensive_crops": _crop_labels(expensive_crops),
        "plans": [],
        "rejections": [rejection],
        "changed_routes": [],
        "changed_steps": {},
        "invariants": {
            "actor_surface_exact": True,
            "inactive_market_suffix_exact": True,
            "seed_quantity_exact": True,
            "branch_topology_exact": True,
            "route_rows_well_formed": reason != "malformed_route_row",
            "base_compiler_exact": base_blob == EXPECTED_BASE_COMPILER_GIT_BLOB,
            "inherited_market_rows_same_index_exact": True,
            "staged_orders_after_inherited_live_rows": True,
        },
        "order_rail": {
            "schema_version": ORDER_RAIL_SCHEMA,
            "base_compiler_expected_git_blob": EXPECTED_BASE_COMPILER_GIT_BLOB,
            "base_compiler_actual_git_blob": base_blob,
            "placement_policy": "append_or_trailing_active_prefix_blank_only",
        },
    }


def _validate_routes(
    routes: Any,
    *,
    max_orders: Any,
    turns_per_day: Any,
    expensive_crops: Any,
    first_day_only: Any,
) -> tuple[str, dict[str, Any]] | None:
    if not isinstance(routes, Mapping) or not routes:
        return "empty_or_non_mapping_routes", {}
    if type(max_orders) is not int or max_orders <= 0:
        return "invalid_max_orders", {}
    if type(turns_per_day) is not int or turns_per_day <= 1:
        return "invalid_turns_per_day", {}
    if type(first_day_only) is not bool:
        return "invalid_first_day_only", {}
    if isinstance(expensive_crops, (str, bytes, bytearray)) or not isinstance(
        expensive_crops, Sequence
    ):
        return "invalid_expensive_crops", {}
    if any(type(crop) is not str or not crop for crop in expensive_crops):
        return "invalid_expensive_crops", {}

    labels: dict[str, Any] = {}
    for route_name, route in routes.items():
        label = str(route_name)
        if label in labels and labels[label] != route_name:
            return "ambiguous_route_labels", {"route": label}
        labels[label] = route_name
        if isinstance(route, (str, bytes, bytearray)) or not isinstance(route, Sequence):
            return "malformed_route_row", {"route": label, "row_kind": "route"}
        for step, action in enumerate(route):
            if not isinstance(action, Mapping):
                return "malformed_route_row", {
                    "route": label,
                    "step": step,
                    "row_kind": "action",
                }
            market = action.get("market", [])
            farmer = action.get("farmer", [])
            hands = action.get("hands", [])
            if not isinstance(market, list) or not isinstance(farmer, list) or not isinstance(hands, list):
                return "malformed_route_row", {
                    "route": label,
                    "step": step,
                    "row_kind": "surface",
                }
            units = [farmer, *hands]
            if any(not isinstance(unit, list) for unit in units):
                return "malformed_route_row", {
                    "route": label,
                    "step": step,
                    "row_kind": "unit",
                }
            for unit_slot, unit in enumerate(units):
                if not unit:
                    continue
                if type(unit[0]) is not str:
                    return "malformed_route_row", {
                        "route": label,
                        "step": step,
                        "slot": unit_slot,
                        "row_kind": "unit_opcode",
                    }
                if unit[0] == "PLANT" and (
                    len(unit) < 2 or type(unit[1]) is not str or not unit[1]
                ):
                    return "malformed_route_row", {
                        "route": label,
                        "step": step,
                        "slot": unit_slot,
                        "row_kind": "plant",
                    }
            for slot, order in enumerate(market):
                if not isinstance(order, list):
                    return "malformed_route_row", {
                        "route": label,
                        "step": step,
                        "slot": slot,
                        "row_kind": "market",
                    }
                if not order:
                    continue
                if type(order[0]) is not str or not order[0]:
                    return "malformed_route_row", {
                        "route": label,
                        "step": step,
                        "slot": slot,
                        "row_kind": "market_opcode",
                    }
                if order[0] in _QUANTITY_ORDERS:
                    if (
                        len(order) < 3
                        or type(order[1]) is not str
                        or not order[1]
                        or type(order[2]) is not int
                        or order[2] < 0
                    ):
                        return "malformed_route_row", {
                            "route": label,
                            "step": step,
                            "slot": slot,
                            "row_kind": "market_quantity",
                            "opcode": order[0],
                        }
    return None


def _place_seed_order_after_inherited(
    action: dict[str, Any],
    crop: str,
    quantity: int,
    max_orders: int,
) -> tuple[bool, int | None]:
    """Place only after every inherited nonblank row in the active prefix."""
    market = action["market"]
    active_length = min(len(market), max_orders)
    last_live = max(
        (slot for slot, row in enumerate(market[:active_length]) if row),
        default=-1,
    )

    # Appending is always later than every inherited row when below the cap.
    if len(market) < max_orders:
        market.append(["BUY_SEED", crop, quantity])
        return True, len(market) - 1

    # At the cap, only a trailing active-prefix blank is safe.  An internal hole
    # before any live row would advance the seed purchase ahead of that row.
    for slot in range(last_live + 1, active_length):
        if not market[slot]:
            market[slot] = ["BUY_SEED", crop, quantity]
            return True, slot
    return False, None


def _clone_function(function: Any, **overrides: Any) -> Any:
    namespace = dict(function.__globals__)
    namespace.update(overrides)
    clone = FunctionType(
        function.__code__,
        namespace,
        function.__name__,
        function.__defaults__,
        function.__closure__,
    )
    clone.__kwdefaults__ = deepcopy(function.__kwdefaults__)
    clone.__annotations__ = dict(getattr(function, "__annotations__", {}))
    return clone


def _isolated_compiler() -> Any:
    safe_apply = _clone_function(
        _base._apply_candidate,
        _place_seed_order=_place_seed_order_after_inherited,
    )
    return _clone_function(
        _base.compile_jit_expensive_seed_routes,
        _apply_candidate=safe_apply,
    )


def _route_key_by_label(routes: Mapping[Any, Any]) -> dict[str, Any]:
    return {str(key): key for key in routes}


def _verify_changed_surface(
    original: Mapping[Any, Sequence[Mapping[str, Any]]],
    staged: Mapping[Any, Sequence[Mapping[str, Any]]],
    report: Mapping[str, Any],
    max_orders: int,
) -> tuple[bool, dict[str, Any]]:
    labels = _route_key_by_label(original)
    allowed: dict[tuple[str, int, int], tuple[str, int, bool]] = {}
    anchors: dict[tuple[str, int, int], str] = {}
    placement_count = 0

    plans = report.get("plans")
    if not isinstance(plans, list):
        return False, {"reason": "plans_not_list"}
    for plan in plans:
        if not isinstance(plan, Mapping):
            return False, {"reason": "plan_not_mapping"}
        crop = plan.get("crop")
        anchor_step = plan.get("anchor_step")
        anchor_slot = plan.get("anchor_slot")
        placements = plan.get("placements")
        if (
            type(crop) is not str
            or type(anchor_step) is not int
            or type(anchor_slot) is not int
            or not isinstance(placements, Mapping)
        ):
            return False, {"reason": "malformed_plan_receipt"}
        plan_routes = plan.get("routes")
        if (
            not isinstance(plan_routes, list)
            or not plan_routes
            or any(type(label) is not str or label not in labels for label in plan_routes)
            or len(set(plan_routes)) != len(plan_routes)
        ):
            return False, {"reason": "malformed_plan_routes"}
        for label in plan_routes:
            anchor_key = (label, anchor_step, anchor_slot)
            if anchor_key in anchors and anchors[anchor_key] != crop:
                return False, {"reason": "duplicate_anchor", "route": label}
            anchors[anchor_key] = crop
        for label, rows in placements.items():
            if (
                type(label) is not str
                or label not in labels
                or label not in plan_routes
                or not isinstance(rows, list)
            ):
                return False, {"reason": "malformed_placement_route", "route": label}
            route_key = labels[label]
            for placement in rows:
                if not isinstance(placement, Mapping):
                    return False, {"reason": "malformed_placement"}
                step = placement.get("step")
                slot = placement.get("slot")
                quantity = placement.get("quantity")
                if (
                    type(step) is not int
                    or type(slot) is not int
                    or type(quantity) is not int
                    or quantity <= 0
                    or step < 0
                    or step >= len(original[route_key])
                    or slot < 0
                    or slot >= max_orders
                ):
                    return False, {"reason": "malformed_placement_coordinates"}
                is_anchor = step == anchor_step and slot == anchor_slot
                key = (label, step, slot)
                if key in allowed:
                    return False, {"reason": "duplicate_placement", "route": label, "step": step, "slot": slot}
                allowed[key] = (crop, quantity, is_anchor)
                placement_count += 1

                before_market = original[route_key][step].get("market", [])
                after_market = staged[route_key][step].get("market", [])
                if slot >= len(after_market) or after_market[slot] != ["BUY_SEED", crop, quantity]:
                    return False, {"reason": "placement_not_installed", "route": label, "step": step, "slot": slot}
                if is_anchor:
                    if slot >= len(before_market):
                        return False, {"reason": "anchor_missing", "route": label, "step": step, "slot": slot}
                    prior = before_market[slot]
                    if not (
                        isinstance(prior, list)
                        and len(prior) >= 3
                        and prior[0] == "BUY_SEED"
                        and prior[1] == crop
                    ):
                        return False, {"reason": "anchor_identity_drift", "route": label, "step": step, "slot": slot}
                else:
                    last_live = max(
                        (index for index, row in enumerate(before_market[:max_orders]) if row),
                        default=-1,
                    )
                    if slot <= last_live:
                        return False, {
                            "reason": "placement_precedes_inherited_live_row",
                            "route": label,
                            "step": step,
                            "slot": slot,
                            "last_inherited_live_slot": last_live,
                        }
                    if slot < len(before_market) and before_market[slot]:
                        return False, {"reason": "placement_overwrote_live_row", "route": label, "step": step, "slot": slot}

    if set(staged) != set(original):
        return False, {"reason": "route_key_drift"}

    changed_positions: list[dict[str, Any]] = []
    observed_allowed: set[tuple[str, int, int]] = set()
    for route_key, before_route in original.items():
        label = str(route_key)
        after_route = staged.get(route_key)
        if (
            isinstance(after_route, (str, bytes, bytearray))
            or not isinstance(after_route, Sequence)
            or len(after_route) != len(before_route)
        ):
            return False, {"reason": "route_shape_drift", "route": label}
        for step, (before_action, after_action) in enumerate(zip(before_route, after_route)):
            if not isinstance(after_action, Mapping):
                return False, {"reason": "action_shape_drift", "route": label, "step": step}
            if before_action.get("farmer", []) != after_action.get("farmer", []) or before_action.get("hands", []) != after_action.get("hands", []):
                return False, {"reason": "actor_surface_drift", "route": label, "step": step}
            before_nonmarket = {key: value for key, value in before_action.items() if key != "market"}
            after_nonmarket = {key: value for key, value in after_action.items() if key != "market"}
            if before_nonmarket != after_nonmarket:
                return False, {"reason": "nonmarket_action_surface_drift", "route": label, "step": step}
            before_market = before_action.get("market", [])
            after_market = after_action.get("market", [])
            if before_market[max_orders:] != after_market[max_orders:]:
                return False, {"reason": "inactive_market_suffix_drift", "route": label, "step": step}
            width = max(min(len(before_market), max_orders), min(len(after_market), max_orders))
            for slot in range(width):
                before_row = before_market[slot] if slot < len(before_market) else None
                after_row = after_market[slot] if slot < len(after_market) else None
                if before_row == after_row:
                    continue
                key = (label, step, slot)
                receipt = allowed.get(key)
                if receipt is None and key not in anchors:
                    return False, {"reason": "unreported_market_change", "route": label, "step": step, "slot": slot}
                changed_positions.append({"route": label, "step": step, "slot": slot})
                if receipt is not None:
                    observed_allowed.add(key)

            for slot, before_row in enumerate(before_market[:max_orders]):
                if not before_row:
                    continue
                key = (label, step, slot)
                receipt = allowed.get(key)
                if key in anchors:
                    crop = anchors[key]
                    if not (
                        isinstance(before_row, list)
                        and len(before_row) >= 3
                        and before_row[0] == "BUY_SEED"
                        and before_row[1] == crop
                        and type(before_row[2]) is int
                        and before_row[2] > 0
                    ):
                        return False, {
                            "reason": "anchor_identity_drift",
                            "route": label,
                            "step": step,
                            "slot": slot,
                        }
                    after_row = after_market[slot] if slot < len(after_market) else None
                    if after_row:
                        if not (
                            isinstance(after_row, list)
                            and len(after_row) == 3
                            and after_row[0] == "BUY_SEED"
                            and after_row[1] == crop
                            and type(after_row[2]) is int
                            and 0 < after_row[2] <= before_row[2]
                        ):
                            return False, {
                                "reason": "anchor_result_invalid",
                                "route": label,
                                "step": step,
                                "slot": slot,
                            }
                        if receipt is None or not receipt[2] or receipt[1] != after_row[2]:
                            return False, {
                                "reason": "retained_anchor_not_receipted",
                                "route": label,
                                "step": step,
                                "slot": slot,
                            }
                    elif receipt is not None:
                        return False, {
                            "reason": "empty_anchor_has_positive_receipt",
                            "route": label,
                            "step": step,
                            "slot": slot,
                        }
                    continue
                if receipt is not None and receipt[2]:
                    return False, {
                        "reason": "anchor_receipt_without_anchor",
                        "route": label,
                        "step": step,
                        "slot": slot,
                    }
                if slot >= len(after_market) or after_market[slot] != before_row:
                    return False, {"reason": "inherited_row_not_same_index_exact", "route": label, "step": step, "slot": slot}

    unobserved = sorted(set(allowed) - observed_allowed)
    if unobserved:
        label, step, slot = unobserved[0]
        return False, {
            "reason": "placement_receipt_without_change",
            "route": label,
            "step": step,
            "slot": slot,
        }
    if report.get("certified") and not changed_positions:
        return False, {"reason": "certified_without_market_change"}

    return True, {
        "schema_version": ORDER_RAIL_SCHEMA,
        "base_compiler_expected_git_blob": EXPECTED_BASE_COMPILER_GIT_BLOB,
        "placement_policy": "append_or_trailing_active_prefix_blank_only",
        "placement_count": placement_count,
        "changed_positions": changed_positions,
    }


def compile_jit_expensive_seed_routes(
    routes: Mapping[Any, Sequence[Mapping[str, Any]]],
    *,
    max_orders: int = 10,
    turns_per_day: int = 24,
    expensive_crops: Sequence[str] = _base.DEFAULT_EXPENSIVE_CROPS,
    first_day_only: bool = True,
) -> tuple[dict[Any, list[dict[str, Any]]], dict[str, Any]]:
    """Compile Capillary routes while preserving every inherited row's priority."""
    base_blob, base_error = _base_blob()
    try:
        invalid = _validate_routes(
            routes,
            max_orders=max_orders,
            turns_per_day=turns_per_day,
            expensive_crops=expensive_crops,
            first_day_only=first_day_only,
        )
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError) as error:
        invalid = (
            "compiler_input_validation_failed",
            {"error_type": type(error).__name__},
        )
    if invalid is not None:
        reason, detail = invalid
        return _failure_report(
            routes,
            reason=reason,
            max_orders=max_orders,
            turns_per_day=turns_per_day,
            expensive_crops=expensive_crops,
            first_day_only=first_day_only,
            detail=detail,
            base_blob=base_blob,
        )

    if base_blob != EXPECTED_BASE_COMPILER_GIT_BLOB:
        return _failure_report(
            routes,
            reason="base_compiler_blob_mismatch",
            max_orders=max_orders,
            turns_per_day=turns_per_day,
            expensive_crops=expensive_crops,
            first_day_only=first_day_only,
            detail={"error_type": base_error},
            base_blob=base_blob,
        )

    original = _copy_routes(routes)
    try:
        compiler = _isolated_compiler()
        staged, report = compiler(
            original,
            max_orders=max_orders,
            turns_per_day=turns_per_day,
            expensive_crops=expensive_crops,
            first_day_only=first_day_only,
        )
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError) as error:
        return _failure_report(
            original,
            reason="base_compiler_execution_failed",
            max_orders=max_orders,
            turns_per_day=turns_per_day,
            expensive_crops=expensive_crops,
            first_day_only=first_day_only,
            detail={"error_type": type(error).__name__},
            base_blob=base_blob,
        )

    if not isinstance(report, dict):
        return _failure_report(
            original,
            reason="base_compiler_report_invalid",
            max_orders=max_orders,
            turns_per_day=turns_per_day,
            expensive_crops=expensive_crops,
            first_day_only=first_day_only,
            base_blob=base_blob,
        )

    report = deepcopy(report)
    report.setdefault("invariants", {})
    report["invariants"]["route_rows_well_formed"] = True
    report["invariants"]["base_compiler_exact"] = True
    report["invariants"]["inherited_market_rows_same_index_exact"] = True
    report["invariants"]["staged_orders_after_inherited_live_rows"] = True
    report["order_rail"] = {
        "schema_version": ORDER_RAIL_SCHEMA,
        "base_compiler_expected_git_blob": EXPECTED_BASE_COMPILER_GIT_BLOB,
        "base_compiler_actual_git_blob": base_blob,
        "placement_policy": "append_or_trailing_active_prefix_blank_only",
        "placement_count": 0,
        "changed_positions": [],
    }
    if not report.get("certified"):
        return staged, report

    exact, detail = _verify_changed_surface(original, staged, report, max_orders)
    if not exact:
        return _failure_report(
            original,
            reason="order_rail_postcondition_failed",
            max_orders=max_orders,
            turns_per_day=turns_per_day,
            expensive_crops=expensive_crops,
            first_day_only=first_day_only,
            detail=detail,
            base_blob=base_blob,
        )
    detail["base_compiler_actual_git_blob"] = base_blob
    report["order_rail"] = detail
    return staged, report
