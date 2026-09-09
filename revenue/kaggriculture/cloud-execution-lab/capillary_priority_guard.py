# SPDX-License-Identifier: Apache-2.0
"""Priority-safe carrier for the isolated Capillary JIT seed compiler.

The predecessor compiler placed a staged BUY_SEED into the first blank active
market slot.  A blank before an inherited order is not free execution capacity:
the seed can spend cash first and make a previously filled HIRE, BUY_LAND,
BUY_PRODUCT, BUY_ANIMAL, or SELL fail.  This module executes the exact compiler
in a private module graph with one placement primitive changed: injected seed
orders may use only a slot strictly after every inherited nonblank active row.

The returned route map is additionally audited against the input.  Any priority
violation, inherited-row mutation, malformed compiler result, or partial unsafe
route causes an exact whole-map rollback.  This module does not mutate the
shared ``jit_seed_staging`` module or any canonical/runtime bytes.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Mapping, Sequence
import uuid


_RULE = "injected_seed_after_all_inherited_nonblank_active_rows"
_MISSING = object()
_EXPECTED_OP = "BUY_SEED"


def _json_safe_label(value: Any) -> str:
    return str(value)


def _positive_quantity(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        quantity = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return quantity if quantity > 0 else None


def _positive_seed(row: Any) -> tuple[str, int] | None:
    if not isinstance(row, list) or len(row) < 3 or row[0] != _EXPECTED_OP:
        return None
    crop = row[1]
    quantity = _positive_quantity(row[2])
    if not isinstance(crop, str) or not crop or quantity is None:
        return None
    return crop, quantity


def _seed_reduction(before: Any, after: Any) -> bool:
    prior = _positive_seed(before)
    if prior is None:
        return False
    if after == []:
        return True
    current = _positive_seed(after)
    return current is not None and current[0] == prior[0] and current[1] <= prior[1]


def _place_seed_order_after_inherited(
    action: dict[str, Any],
    crop: str,
    quantity: int,
    max_orders: int,
) -> tuple[bool, int | None]:
    """Place after all inherited active effects, or reject without mutation."""
    if (
        not isinstance(action, dict)
        or not isinstance(action.get("market"), list)
        or not isinstance(crop, str)
        or not crop
        or _positive_quantity(quantity) is None
        or isinstance(max_orders, bool)
        or not isinstance(max_orders, int)
        or max_orders <= 0
    ):
        return False, None

    market = action["market"]
    active = market[:max_orders]
    last_nonblank = max(
        (slot for slot, row in enumerate(active) if bool(row)),
        default=-1,
    )
    slot = last_nonblank + 1

    if slot < min(len(market), max_orders):
        # By definition of last_nonblank, every existing row at and after this
        # position inside the active prefix is blank.  Use the first trailing
        # blank while preserving list length and every inherited index.
        if market[slot]:
            return False, None
        market[slot] = [_EXPECTED_OP, crop, int(quantity)]
        return True, slot

    if len(market) < max_orders:
        market.append([_EXPECTED_OP, crop, int(quantity)])
        return True, len(market) - 1

    # Interior holes are deliberately unusable: filling one would advance seed
    # spend ahead of an inherited active row.
    return False, None


def _load_private_staging() -> tuple[ModuleType, str]:
    """Load the exact sibling compiler privately and patch only its local seam."""
    path = Path(__file__).resolve().with_name("jit_seed_staging.py")
    source = path.read_bytes()
    source_sha256 = hashlib.sha256(source).hexdigest()
    name = f"_capillary_priority_staging_{source_sha256[:12]}_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load exact Capillary compiler: {path}")
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(name, _MISSING)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is _MISSING:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
    module._place_seed_order = _place_seed_order_after_inherited
    return module, source_sha256


def _detached_original(routes: Any) -> dict[Any, Any]:
    if not isinstance(routes, Mapping):
        return {}
    try:
        return deepcopy(dict(routes))
    except Exception:
        return {}


def _priority_blockers(
    routes: Mapping[Any, Sequence[Mapping[str, Any]]],
    report: Mapping[str, Any],
    max_orders: int,
) -> list[dict[str, Any]]:
    """Identify compiler rejections caused only by an unsafe interior hole."""
    labels: dict[str, list[Any]] = {}
    for key in routes:
        labels.setdefault(_json_safe_label(key), []).append(key)

    blockers: list[dict[str, Any]] = []
    rejections = report.get("rejections", [])
    if not isinstance(rejections, list):
        return [{"reason": "malformed_rejection_list"}]
    for rejection in rejections:
        if not isinstance(rejection, Mapping):
            continue
        if rejection.get("reason") != "no_reserved_active_market_slot":
            continue
        label = rejection.get("route")
        step = rejection.get("step")
        keys = labels.get(str(label), [])
        if len(keys) != 1 or isinstance(step, bool) or not isinstance(step, int):
            blockers.append(
                {
                    "reason": "ambiguous_priority_rejection",
                    "route": str(label),
                    "step": step,
                }
            )
            continue
        route = routes[keys[0]]
        if step < 0 or step >= len(route):
            blockers.append(
                {"reason": "priority_rejection_step_out_of_range", "route": str(label), "step": step}
            )
            continue
        market = route[step].get("market", [])
        if not isinstance(market, list):
            blockers.append(
                {"reason": "priority_rejection_market_malformed", "route": str(label), "step": step}
            )
            continue
        active = market[:max_orders]
        last_nonblank = max(
            (slot for slot, row in enumerate(active) if bool(row)),
            default=-1,
        )
        interior_holes = [
            slot for slot, row in enumerate(active)
            if not row and slot < last_nonblank
        ]
        if len(active) >= max_orders and interior_holes:
            blockers.append(
                {
                    "reason": "no_trailing_priority_safe_slot",
                    "route": str(label),
                    "step": step,
                    "crop": rejection.get("crop"),
                    "last_inherited_nonblank_slot": last_nonblank,
                    "rejected_interior_slots": interior_holes,
                }
            )
    return blockers


def _audit_priority(
    original: Mapping[Any, Sequence[Mapping[str, Any]]],
    staged: Mapping[Any, Sequence[Mapping[str, Any]]],
    max_orders: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Verify candidate changes cannot precede or alter inherited market rows."""
    placements: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []

    if set(original) != set(staged):
        return placements, [{"reason": "route_key_set_changed"}]

    for key in original:
        before_route = original[key]
        after_route = staged[key]
        label = _json_safe_label(key)
        if not isinstance(before_route, Sequence) or not isinstance(after_route, Sequence):
            violations.append({"reason": "route_not_sequence", "route": label})
            continue
        if len(before_route) != len(after_route):
            violations.append(
                {
                    "reason": "route_length_changed",
                    "route": label,
                    "before": len(before_route),
                    "after": len(after_route),
                }
            )
            continue

        route_changed = False
        route_injections = 0
        for step, (before_action, after_action) in enumerate(zip(before_route, after_route)):
            if not isinstance(before_action, Mapping) or not isinstance(after_action, Mapping):
                violations.append({"reason": "action_not_mapping", "route": label, "step": step})
                continue
            before_other = {k: deepcopy(v) for k, v in before_action.items() if k != "market"}
            after_other = {k: deepcopy(v) for k, v in after_action.items() if k != "market"}
            if before_other != after_other:
                violations.append(
                    {"reason": "non_market_action_changed", "route": label, "step": step}
                )

            before_market = before_action.get("market", [])
            after_market = after_action.get("market", [])
            if not isinstance(before_market, list) or not isinstance(after_market, list):
                violations.append({"reason": "market_not_list", "route": label, "step": step})
                continue
            if before_market[max_orders:] != after_market[max_orders:]:
                violations.append(
                    {"reason": "inactive_market_suffix_changed", "route": label, "step": step}
                )

            before_active = before_market[:max_orders]
            after_active = after_market[:max_orders]
            last_inherited = max(
                (slot for slot, row in enumerate(before_active) if bool(row)),
                default=-1,
            )
            width = max(len(before_active), len(after_active))
            for slot in range(width):
                before_row = before_active[slot] if slot < len(before_active) else _MISSING
                after_row = after_active[slot] if slot < len(after_active) else _MISSING
                if before_row == after_row:
                    continue
                route_changed = True

                if before_row is _MISSING or before_row == []:
                    seed = _positive_seed(after_row)
                    if seed is None:
                        violations.append(
                            {
                                "reason": "non_seed_inserted_into_blank",
                                "route": label,
                                "step": step,
                                "slot": slot,
                            }
                        )
                        continue
                    crop, quantity = seed
                    placement = {
                        "route": label,
                        "step": step,
                        "slot": slot,
                        "crop": crop,
                        "quantity": quantity,
                        "last_inherited_nonblank_slot": last_inherited,
                    }
                    placements.append(placement)
                    route_injections += 1
                    if slot <= last_inherited:
                        violations.append({"reason": "seed_precedes_inherited_row", **placement})
                    continue

                if _seed_reduction(before_row, after_row):
                    continue

                violations.append(
                    {
                        "reason": "inherited_active_row_changed",
                        "route": label,
                        "step": step,
                        "slot": slot,
                        "before": deepcopy(before_row),
                        "after": None if after_row is _MISSING else deepcopy(after_row),
                    }
                )

        if route_changed and route_injections == 0:
            violations.append({"reason": "changed_route_without_injected_seed", "route": label})

    placements.sort(key=lambda item: (item["route"], item["step"], item["slot"], item["crop"]))
    violations.sort(
        key=lambda item: (
            str(item.get("route", "")),
            int(item.get("step", -1)) if isinstance(item.get("step", -1), int) else -1,
            int(item.get("slot", -1)) if isinstance(item.get("slot", -1), int) else -1,
            str(item.get("reason", "")),
        )
    )
    return placements, violations


def _rejected_report(
    report: Mapping[str, Any] | None,
    *,
    source_sha256: str | None,
    reason: str,
    violations: list[dict[str, Any]],
) -> dict[str, Any]:
    result = deepcopy(dict(report or {}))
    attempted = deepcopy(result.get("plans", []))
    result.update(
        {
            "changed": False,
            "certified": False,
            "reason": reason,
            "plans": [],
            "changed_routes": [],
            "changed_steps": {},
        }
    )
    result["priority_safety"] = {
        "schema_version": 1,
        "rule": _RULE,
        "checked": True,
        "safe": False,
        "compiler_source_sha256": source_sha256,
        "attempted_plans": attempted,
        "placements": [],
        "violations": deepcopy(violations),
    }
    return result


def compile_priority_safe_jit_seed_routes(
    routes: Mapping[Any, Sequence[Mapping[str, Any]]],
    *,
    max_orders: int = 10,
    turns_per_day: int = 24,
    expensive_crops: Sequence[str] = ("MELON", "STRAWBERRY"),
    first_day_only: bool = True,
) -> tuple[dict[Any, list[dict[str, Any]]], dict[str, Any]]:
    """Compile Capillary routes with fail-closed same-turn priority custody."""
    original = _detached_original(routes)
    source_sha256: str | None = None
    try:
        module, source_sha256 = _load_private_staging()
        staged, report = module.compile_jit_expensive_seed_routes(
            routes,
            max_orders=max_orders,
            turns_per_day=turns_per_day,
            expensive_crops=expensive_crops,
            first_day_only=first_day_only,
        )
    except Exception as error:
        return original, _rejected_report(
            None,
            source_sha256=source_sha256,
            reason="compiler_input_invalid",
            violations=[{"reason": "compiler_exception", "error_type": type(error).__name__}],
        )

    if not isinstance(report, Mapping) or not isinstance(staged, Mapping):
        return original, _rejected_report(
            report if isinstance(report, Mapping) else None,
            source_sha256=source_sha256,
            reason="priority_audit_invalid",
            violations=[{"reason": "malformed_compiler_result"}],
        )

    blockers = _priority_blockers(routes, report, max_orders)
    if blockers:
        return original, _rejected_report(
            report,
            source_sha256=source_sha256,
            reason="priority_unsafe",
            violations=blockers,
        )

    if not report.get("certified") or not report.get("changed"):
        result = deepcopy(dict(report))
        result["priority_safety"] = {
            "schema_version": 1,
            "rule": _RULE,
            "checked": False,
            "safe": False,
            "compiler_source_sha256": source_sha256,
            "attempted_plans": [],
            "placements": [],
            "violations": [],
            "reason": "no_certified_change",
        }
        return deepcopy(dict(staged)), result

    placements, violations = _audit_priority(original, staged, max_orders)
    if violations or not placements:
        if not violations:
            violations = [{"reason": "certified_change_without_injected_seed"}]
        return original, _rejected_report(
            report,
            source_sha256=source_sha256,
            reason="priority_audit_failed",
            violations=violations,
        )

    result = deepcopy(dict(report))
    result["priority_safety"] = {
        "schema_version": 1,
        "rule": _RULE,
        "checked": True,
        "safe": True,
        "compiler_source_sha256": source_sha256,
        "attempted_plans": deepcopy(result.get("plans", [])),
        "placements": placements,
        "violations": [],
    }
    return deepcopy(dict(staged)), result


# Keep the candidate runtime's historical patch seam stable for lifecycle tests.
compile_jit_expensive_seed_routes = compile_priority_safe_jit_seed_routes


__all__ = [
    "compile_jit_expensive_seed_routes",
    "compile_priority_safe_jit_seed_routes",
]
