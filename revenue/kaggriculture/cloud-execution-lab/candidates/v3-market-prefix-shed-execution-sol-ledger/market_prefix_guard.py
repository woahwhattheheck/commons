# SPDX-License-Identifier: Apache-2.0
"""Fail-closed custody for inherited shed-occupying market purchases.

The Kaggriculture engine truncates the raw market list first, then processes
orders at literal indices.  SELL quantities can therefore change whether a
later BUY_PRODUCT or BUY_ANIMAL reaches a full shed.  A whole-row occupancy
summary is not a proof that those operating purchases still execute.

This module provides two deliberately separate tools:

* ``trace_capacity_prefix`` mirrors the engine's per-order shed-capacity
  transitions while intentionally ignoring cash and rival-price effects.  It
  is an audit instrument, not a gameplay estimator.
* ``preserves_purchase_prefix`` proves the stronger, rival-independent custody
  condition used for admission: every raw row through the last inherited
  shed-occupying purchase is raw-JSON value-identical.  Under equal pre-state,
  configuration and rival action, the official deterministic interpreter must
  therefore produce the same result for every such purchase.

Ambiguous/malformed inputs fail closed and never raise.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

PRODUCTS = frozenset(
    {
        "WHEAT",
        "CARROT",
        "TOMATO",
        "STRAWBERRY",
        "MELON",
        "EGG",
        "MILK",
        "WOOL",
        "FERTILIZER",
    }
)
BUY_PRODUCTS = frozenset({"WHEAT", "FERTILIZER"})
ANIMALS = frozenset({"GOOSE", "COW", "SHEEP"})
QUANTITY_OPS = frozenset({"BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"})
PURCHASE_OPS = frozenset({"BUY_PRODUCT", "BUY_ANIMAL"})
_MISSING = object()


class InputError(ValueError):
    """Raised internally for a value that cannot satisfy the engine contract."""


def _engine_int(value: Any) -> int:
    """Use the official engine's ``int(value)`` semantics, but make them total."""
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise InputError("not an engine integer") from exc


def market_limit(config: Mapping[str, Any] | None) -> int:
    """Return ``max(1, int(maxMarketOrdersPerTurn))`` or fail closed."""
    if config is not None and not isinstance(config, Mapping):
        raise InputError("configuration is not a mapping")
    raw = (config or {}).get("maxMarketOrdersPerTurn", 10)
    return max(1, _engine_int(raw))


def shed_capacity(config: Mapping[str, Any] | None) -> int:
    """Return the exact integer shed capacity or fail closed."""
    if config is not None and not isinstance(config, Mapping):
        raise InputError("configuration is not a mapping")
    cap = _engine_int((config or {}).get("shedCapacity", 100))
    if cap < 0:
        raise InputError("negative shed capacity")
    return cap


def parse_order(order: Any) -> dict[str, Any] | None:
    """Total structural mirror of the official ``_parse_order``.

    Item-domain validation remains explicit so JSON arrays or mappings in the
    item/op positions cannot trigger unhashable-membership exceptions.
    """
    if not isinstance(order, list) or not order:
        return None
    op = order[0]
    if not isinstance(op, str):
        return None
    if op in ("HIRE", "BUY_LAND"):
        return {"type": op}
    if op not in QUANTITY_OPS or len(order) < 3:
        return None
    try:
        quantity = _engine_int(order[2])
    except InputError:
        return None
    if quantity <= 0:
        return None
    item = order[1]
    if not isinstance(item, str):
        return None
    if op == "SELL" and item not in PRODUCTS:
        return None
    if op == "BUY_PRODUCT" and item not in BUY_PRODUCTS:
        return None
    if op == "BUY_ANIMAL" and item not in ANIMALS:
        return None
    # BUY_SEED does not touch shed occupancy.  Crop-domain validity is not
    # needed by this guard; an invalid seed row is still occupancy-inert.
    return {"type": op, "item": item, "remaining": quantity}


def _nonnegative_stock(shed: Mapping[str, Any]) -> dict[str, int]:
    if not isinstance(shed, Mapping):
        raise InputError("shed is not a mapping")
    out: dict[str, int] = {}
    for item, raw in shed.items():
        if not isinstance(item, str):
            raise InputError("shed key is not a string")
        amount = _engine_int(raw)
        if amount < 0:
            raise InputError("negative shed stock")
        if amount:
            out[item] = amount
    return out


def trace_capacity_prefix(
    market: Any,
    shed: Mapping[str, Any],
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Trace only deterministic shed-capacity effects in the executable prefix.

    Cash, market price and rival action are intentionally outside this trace.
    The returned ``committed`` quantity for purchases is therefore the maximum
    quantity admitted by shed capacity, not a claim that cash also permits it.
    This separation keeps the predecessor witness exact and auditable.
    """
    try:
        limit = market_limit(config)
        cap = shed_capacity(config)
        if not isinstance(market, list):
            raise InputError("market is not a list")
        stock = _nonnegative_stock(shed)
    except InputError as exc:
        return {
            "ok": False,
            "reason": "BAD_INPUT",
            "detail": str(exc),
            "events": [],
        }

    events: list[dict[str, Any]] = []
    for index, raw in enumerate(market[:limit]):
        parsed = parse_order(raw)
        if parsed is None:
            events.append(
                {
                    "index": index,
                    "type": "NO_OP",
                    "committed": 0,
                    "occupancy_after": sum(stock.values()),
                }
            )
            continue
        op = parsed["type"]
        item = parsed.get("item")
        requested = int(parsed.get("remaining", 0))
        committed = 0
        if op == "SELL":
            committed = min(requested, stock.get(item, 0))
            if committed:
                left = stock.get(item, 0) - committed
                if left:
                    stock[item] = left
                else:
                    stock.pop(item, None)
        elif op in PURCHASE_OPS:
            room = max(0, cap - sum(stock.values()))
            committed = min(requested, room)
            if committed:
                stock[item] = stock.get(item, 0) + committed
        events.append(
            {
                "index": index,
                "type": op,
                "item": item,
                "requested": requested,
                "committed": committed,
                "occupancy_after": sum(stock.values()),
            }
        )
    return {
        "ok": True,
        "reason": "TRACED",
        "limit": limit,
        "capacity": cap,
        "initial_occupancy": sum(_nonnegative_stock(shed).values()),
        "final_occupancy": sum(stock.values()),
        "final_shed": stock,
        "events": events,
    }



def sell_only_scheduler_delta(
    baseline_market: Any,
    candidate_market: Any,
) -> tuple[bool, dict[str, Any]]:
    """Prove that the candidate changed only scheduler-owned SELL quantities.

    The current scheduler preserves every inherited row index, may replace an
    inherited valid SELL with ``[]`` or the same item at another positive
    quantity, and may append new valid SELL rows.  It does not fill inherited
    blanks, reorder rows, change items, edit purchases/hires, or shorten the
    inherited list.  This total predicate makes that mutation boundary
    executable rather than trusting the caller's label.
    """
    report: dict[str, Any] = {
        "safe": False,
        "reason": "BAD_MARKET_QUEUE",
        "differing_indices": [],
    }
    if not isinstance(baseline_market, list) or not isinstance(candidate_market, list):
        return False, report
    if len(candidate_market) < len(baseline_market):
        report.update(reason="INHERITED_ROW_REMOVED")
        return False, report

    differences: list[int] = []
    for index, before in enumerate(baseline_market):
        after = candidate_market[index]
        if before == after:
            continue
        differences.append(index)
        parsed_before = parse_order(before)
        if parsed_before is None or parsed_before.get("type") != "SELL":
            report.update(
                reason="NON_SELL_INHERITED_ROW_CHANGED",
                differing_indices=differences,
                rejected_index=index,
            )
            return False, report
        if after == []:
            continue
        parsed_after = parse_order(after)
        if (
            parsed_after is None
            or parsed_after.get("type") != "SELL"
            or parsed_after.get("item") != parsed_before.get("item")
            or not isinstance(after, list)
            or len(after) != 3
        ):
            report.update(
                reason="SELL_ROW_MUTATION_OUTSIDE_QUANTITY",
                differing_indices=differences,
                rejected_index=index,
            )
            return False, report

    for index in range(len(baseline_market), len(candidate_market)):
        after = candidate_market[index]
        differences.append(index)
        parsed_after = parse_order(after)
        if (
            parsed_after is None
            or parsed_after.get("type") != "SELL"
            or not isinstance(after, list)
            or len(after) != 3
        ):
            report.update(
                reason="NON_SELL_ROW_APPENDED",
                differing_indices=differences,
                rejected_index=index,
            )
            return False, report

    report.update(
        safe=True,
        reason="SELL_ONLY_SCHEDULER_DELTA",
        differing_indices=differences,
    )
    return True, report

def inherited_purchase_indices(
    baseline_market: Any,
    config: Mapping[str, Any] | None = None,
) -> tuple[int, ...]:
    """Return valid shed-occupying purchase indices in the raw engine prefix."""
    if not isinstance(baseline_market, list):
        raise InputError("baseline market is not a list")
    limit = market_limit(config)
    found: list[int] = []
    for index, raw in enumerate(baseline_market[:limit]):
        parsed = parse_order(raw)
        if parsed is not None and parsed["type"] in PURCHASE_OPS:
            found.append(index)
    return tuple(found)


def preserves_purchase_prefix(
    baseline_market: Any,
    candidate_market: Any,
    config: Mapping[str, Any] | None = None,
) -> tuple[bool, dict[str, Any]]:
    """Prove exact raw-prefix custody through the last inherited purchase.

    Equality is intentionally stronger than an occupancy-only simulation.  It
    closes cash, price, paired-rival, malformed-row and partial-order ambiguity
    at once: the interpreter sees the same own raw prefix through every guarded
    purchase.  Rows after the last purchase remain free for SELL scheduling.
    """
    report: dict[str, Any] = {
        "safe": False,
        "reason": "BAD_INPUT",
        "purchase_indices": [],
        "differing_indices": [],
    }
    try:
        if not isinstance(candidate_market, list):
            raise InputError("candidate market is not a list")
        purchases = inherited_purchase_indices(baseline_market, config)
        limit = market_limit(config)
    except InputError as exc:
        report["detail"] = str(exc)
        return False, report

    report["limit"] = limit
    report["purchase_indices"] = list(purchases)
    if not purchases:
        report.update(safe=True, reason="NO_INHERITED_SHED_PURCHASE")
        return True, report

    boundary = purchases[-1]
    report["guarded_through_index"] = boundary
    differences: list[int] = []
    for index in range(boundary + 1):
        before = baseline_market[index] if index < len(baseline_market) else _MISSING
        after = candidate_market[index] if index < len(candidate_market) else _MISSING
        if before is _MISSING or after is _MISSING or before != after:
            differences.append(index)
    report["differing_indices"] = differences
    if differences:
        report["reason"] = "PURCHASE_PREFIX_CHANGED"
        return False, report
    report.update(safe=True, reason="PURCHASE_PREFIX_IDENTICAL")
    return True, report



def preserves_scheduler_contract(
    baseline_market: Any,
    candidate_market: Any,
    config: Mapping[str, Any] | None = None,
) -> tuple[bool, dict[str, Any]]:
    """Combine SELL-only mutation custody with inherited-purchase custody."""
    delta_safe, delta = sell_only_scheduler_delta(baseline_market, candidate_market)
    report: dict[str, Any] = {"safe": False, "delta": delta}
    if not delta_safe:
        report["reason"] = delta["reason"]
        return False, report
    prefix_safe, prefix = preserves_purchase_prefix(
        baseline_market, candidate_market, config
    )
    report["prefix"] = prefix
    report["reason"] = prefix["reason"]
    report["safe"] = prefix_safe
    return prefix_safe, report

def guard_candidate_action(
    baseline_action: Any,
    candidate_action: Any,
    config: Mapping[str, Any] | None = None,
    *,
    enabled: bool = False,
) -> tuple[Any, dict[str, Any]]:
    """Return candidate when proven safe, otherwise atomically return baseline.

    This is a transport-safe reference wrapper.  A stateful scheduler should
    use ``preserves_scheduler_contract`` as a feasibility veto *before* committing
    future-plan state, rather than relying on post-hoc action reversion.
    """
    report: dict[str, Any] = {
        "enabled": bool(enabled),
        "changed": False,
        "reason": "OFF" if not enabled else "BAD_ACTION",
    }
    if not enabled:
        return candidate_action, report
    if not isinstance(baseline_action, Mapping) or not isinstance(candidate_action, Mapping):
        report["detail"] = "actions must be mappings"
        return deepcopy(baseline_action), report

    baseline_non_market = {k: v for k, v in baseline_action.items() if k != "market"}
    candidate_non_market = {k: v for k, v in candidate_action.items() if k != "market"}
    if baseline_non_market != candidate_non_market:
        report.update(changed=True, reason="NON_MARKET_ACTION_CHANGED")
        return deepcopy(baseline_action), report

    safe, contract = preserves_scheduler_contract(
        baseline_action.get("market", []), candidate_action.get("market", []), config
    )
    report["contract"] = contract
    if safe:
        report["reason"] = contract["reason"]
        return candidate_action, report
    report.update(changed=True, reason=contract["reason"])
    return deepcopy(baseline_action), report
