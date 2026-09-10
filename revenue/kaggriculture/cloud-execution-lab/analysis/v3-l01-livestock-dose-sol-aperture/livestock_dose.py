# SPDX-License-Identifier: Apache-2.0
"""Bounded replay-derived livestock substitution for a canonical route tape.

The predecessor L01 ``SHEEP`` arm rewrote every post-opening COW purchase and
collapsed across the retained six-opponent panel.  This module isolates the
missing dose response: preserve the opening pair and convert only the first N
*complete* post-opening COW orders in the canonical MAIN route.

The transform is deliberately narrow:

* only ``BUY_ANIMAL COW <positive-int>`` rows are candidates;
* steps 0 and 1 are never touched;
* no market row is inserted, deleted, moved, resized, or re-quantified;
* a partial order is never split; unsupported doses fail closed to identity;
* farmer actions, hand actions, every other market row, and every other route
  remain byte-for-byte equal as Python values.

Production installation wraps the current instance's lazy ``_initialize`` and
patches each newly constructed controller exactly once.  No environment state,
network, clock, RNG, or opponent identity is read.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping, MutableSequence, Sequence

MAIN_ROUTE_ID = "7015cc00acfa4922"
OPENING_KEEP_THROUGH = 1
# Keep this intervention in the setup phase and before the first public route
# checkpoint at 226. Six days is enough to express a bounded livestock dose
# without turning this back into the rejected all-season rewrite.
LAST_ELIGIBLE_STEP = 143


@dataclass(frozen=True)
class CandidateOrder:
    step: int
    market_index: int
    quantity: int


def _dose(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("dose must be a nonnegative integer")
    return value


def _quantity(order: Sequence[Any]) -> int:
    if len(order) < 3:
        raise ValueError("BUY_ANIMAL COW row is missing a quantity")
    quantity = order[2]
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("BUY_ANIMAL COW quantity must be a positive integer")
    return quantity


def candidate_orders(
    route: Sequence[Mapping[str, Any]],
    *,
    keep_through: int = OPENING_KEEP_THROUGH,
    last_step: int = LAST_ELIGIBLE_STEP,
) -> list[CandidateOrder]:
    """Return eligible COW orders without mutating ``route``.

    Malformed COW rows raise before any caller can mutate. Malformed unrelated
    rows are outside this factor and remain untouched.
    """
    if isinstance(route, (str, bytes)) or not isinstance(route, Sequence):
        raise TypeError("route must be a sequence")
    if isinstance(keep_through, bool) or not isinstance(keep_through, int):
        raise ValueError("keep_through must be an integer")
    if isinstance(last_step, bool) or not isinstance(last_step, int) or last_step <= keep_through:
        raise ValueError("last_step must be an integer after keep_through")

    result: list[CandidateOrder] = []
    upper = min(last_step, len(route) - 1)
    for step in range(max(0, keep_through + 1), upper + 1):
        row = route[step]
        if not isinstance(row, Mapping):
            continue
        market = row.get("market") or []
        if isinstance(market, (str, bytes)) or not isinstance(market, Sequence):
            continue
        for market_index, order in enumerate(market):
            if not isinstance(order, Sequence) or isinstance(order, (str, bytes)) or not order:
                continue
            if order[0] == "BUY_ANIMAL" and len(order) > 1 and order[1] == "COW":
                result.append(CandidateOrder(step, market_index, _quantity(order)))
    return result


def plan_dose(
    route: Sequence[Mapping[str, Any]],
    dose: int,
    *,
    keep_through: int = OPENING_KEEP_THROUGH,
    last_step: int = LAST_ELIGIBLE_STEP,
) -> tuple[list[CandidateOrder], dict[str, Any]]:
    """Plan an exact whole-order dose, or return an identity disposition."""
    requested = _dose(dose)
    orders = candidate_orders(route, keep_through=keep_through, last_step=last_step)
    available_units = sum(order.quantity for order in orders)
    base = {
        "schema_version": 1,
        "route_id": MAIN_ROUTE_ID,
        "requested_units": requested,
        "available_units": available_units,
        "eligible_orders": [
            {"step": order.step, "market_index": order.market_index, "quantity": order.quantity}
            for order in orders
        ],
        "opening_keep_through": keep_through,
        "last_eligible_step": last_step,
    }
    if requested == 0:
        return [], {**base, "changed": False, "converted_units": 0,
                    "converted_orders": 0, "reason": "dose_zero"}

    selected: list[CandidateOrder] = []
    remaining = requested
    for order in orders:
        if remaining == 0:
            break
        if order.quantity > remaining:
            # Splitting would add another executable order or change the
            # original quantity. This factor promises neither, so reject the
            # entire plan rather than silently undershooting or skipping ahead.
            return [], {**base, "changed": False, "converted_units": 0,
                        "converted_orders": 0,
                        "reason": "partial_order_would_change_cardinality",
                        "blocked_order": {"step": order.step,
                                          "market_index": order.market_index,
                                          "quantity": order.quantity,
                                          "remaining_units": remaining}}
        selected.append(order)
        remaining -= order.quantity

    if remaining:
        return [], {**base, "changed": False, "converted_units": 0,
                    "converted_orders": 0, "reason": "insufficient_eligible_units",
                    "remaining_units": remaining}
    return selected, {**base, "changed": True, "converted_units": requested,
                      "converted_orders": len(selected), "reason": "exact_whole_order_dose",
                      "selected_orders": [
                          {"step": order.step, "market_index": order.market_index,
                           "quantity": order.quantity}
                          for order in selected
                      ]}


def apply_route_dose(
    route: MutableSequence[MutableMapping[str, Any]],
    dose: int,
    *,
    keep_through: int = OPENING_KEEP_THROUGH,
    last_step: int = LAST_ELIGIBLE_STEP,
) -> dict[str, Any]:
    """Mutate only the planned animal-name fields and return an exact report."""
    selected, report = plan_dose(
        route, dose, keep_through=keep_through, last_step=last_step
    )
    if not report["changed"]:
        return report

    # Planning validated every selected row before mutation. Revalidate the
    # exact address and quantity to fail before any mutation if a caller raced
    # or supplied an exotic self-modifying container.
    for candidate in selected:
        row = route[candidate.step]
        market = row.get("market") or []
        order = market[candidate.market_index]
        if (not isinstance(order, MutableSequence) or len(order) < 3
                or order[0] != "BUY_ANIMAL" or order[1] != "COW"
                or _quantity(order) != candidate.quantity):
            raise ValueError("route changed between livestock dose planning and application")

    for candidate in selected:
        route[candidate.step]["market"][candidate.market_index][1] = "SHEEP"
    return report


def patch_controller(controller: Any, dose: int) -> dict[str, Any]:
    """Patch the canonical MAIN route only; every other route is untouched."""
    requested = _dose(dose)
    routes = getattr(controller, "R", None)
    if not isinstance(routes, MutableMapping):
        return {"schema_version": 1, "route_id": MAIN_ROUTE_ID,
                "requested_units": requested, "changed": False,
                "converted_units": 0, "converted_orders": 0,
                "reason": "controller_routes_unavailable"}
    route = routes.get(MAIN_ROUTE_ID)
    if not isinstance(route, MutableSequence):
        return {"schema_version": 1, "route_id": MAIN_ROUTE_ID,
                "requested_units": requested, "changed": False,
                "converted_units": 0, "converted_orders": 0,
                "reason": "canonical_main_route_unavailable"}
    return apply_route_dose(route, requested)


def install_after_initialize(instance: Any, dose: int) -> dict[str, Any]:
    """Install a lazy, reconstruction-safe patch on one canonical instance."""
    requested = _dose(dose)
    if getattr(instance, "_livestock_dose_install", None) is not None:
        installed = instance._livestock_dose_install
        if installed["requested_units"] != requested:
            raise ValueError("livestock dose already installed with another value")
        return installed

    cls = type(instance)
    original = getattr(cls, "_initialize", None)
    if not callable(original):
        raise TypeError("canonical instance has no callable _initialize")

    installation = {
        "schema_version": 1,
        "requested_units": requested,
        "status": "installed",
    }
    instance._livestock_dose_install = installation

    def initialize_with_livestock_dose(self: Any, *args: Any, **kwargs: Any) -> Any:
        result = original(self, *args, **kwargs)
        controller = getattr(self, "controller", None)
        token = id(controller)
        if getattr(self, "_livestock_dose_controller_token", None) != token:
            report = patch_controller(controller, requested)
            self._livestock_dose_controller_token = token
            self._livestock_dose_report = report
        else:
            report = getattr(self, "_livestock_dose_report", {
                "schema_version": 1,
                "requested_units": requested,
                "changed": False,
                "converted_units": 0,
                "converted_orders": 0,
                "reason": "controller_already_patched",
            })
        diagnostics = getattr(self, "diagnostics", None)
        if isinstance(diagnostics, MutableMapping):
            diagnostics["v3_livestock_dose"] = dict(report)
        return result

    cls._initialize = initialize_with_livestock_dose
    return installation
