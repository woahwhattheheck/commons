# SPDX-License-Identifier: Apache-2.0
"""Conservatively rescue executable market orders stranded behind empty cap slots.

The Kaggriculture interpreter truncates each raw market list to
``maxMarketOrdersPerTurn`` before parsing orders. An exact empty-list placeholder
inside that prefix therefore consumes one issued slot even though it parses as a
no-op.

The engine also advances both players' queues in lockstep by absolute market
index and refreshes prices after each index. Moving an already-live order across
an interior blank can therefore alter its opponent pairing, quote, affordability,
and terminal result. This module deliberately avoids that compound timing edit:
it activates only when every exact blank in the live prefix is a suffix slot.
Then no already-live non-empty row changes its absolute index.

The bounded transformation is:

* only exact ``[]`` suffix placeholders may move;
* every non-empty value keeps its relative order and value;
* every already-live non-empty row keeps its absolute prefix index;
* a queue changes only when at least one structurally executable order from
  beyond the cap fills a suffix blank; and
* the input object is never mutated.

The function is observation-free. It repairs unused suffix capacity; it does not
retime an already-live purchase, sale, hire, or land order.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping

CROPS = frozenset({"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"})
ANIMALS = frozenset({"GOOSE", "COW", "SHEEP"})
PRODUCTS = frozenset({
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
})
QUANTITY_OPS = frozenset({"BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"})
ATOMIC_OPS = frozenset({"HIRE", "BUY_LAND"})


def _config_value(configuration: Any, key: str, default: Any) -> Any:
    """Read dict-like or Struct-like configuration without mutating it."""
    if configuration is None:
        return default
    if isinstance(configuration, Mapping):
        return configuration.get(key, default)
    return getattr(configuration, key, default)


def market_limit(configuration: Any = None) -> int:
    """Mirror the official engine's lower-bounded market cap."""
    try:
        return max(1, int(_config_value(configuration, "maxMarketOrdersPerTurn", 10)))
    except (TypeError, ValueError, OverflowError):
        # Invalid configuration is an engine-level failure. The candidate must
        # not invent a replacement cap, so fail closed to the canonical default.
        return 10


def is_engine_executable_order(order: Any) -> bool:
    """Recognize orders that can reach an official engine operation handler.

    This is stricter than ``_parse_order`` only for item names: the official
    parser accepts an unknown item, then aborts it during execution. Such a row
    is not evidence that compaction rescued useful work.
    """
    if not isinstance(order, list) or not order:
        return False
    op = order[0]
    if op in ATOMIC_OPS:
        return True
    if op not in QUANTITY_OPS or len(order) < 3:
        return False
    try:
        quantity = int(order[2])
    except (TypeError, ValueError, OverflowError):
        return False
    if quantity <= 0:
        return False
    if op == "BUY_SEED":
        return len(order) > 1 and order[1] in CROPS
    if op == "BUY_ANIMAL":
        return len(order) > 1 and order[1] in ANIMALS
    if op == "BUY_PRODUCT":
        return len(order) > 1 and order[1] in {"WHEAT", "FERTILIZER"}
    return len(order) > 1 and order[1] in PRODUCTS


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def rescue_market_prefix(action: Any, configuration: Any = None):
    """Return ``(action_or_copy, report)`` after one fail-closed suffix fill.

    Exact empty lists are moved behind non-empty tail rows only when the live
    prefix's blanks form a suffix. The edit is committed only when an executable
    row whose original index was outside the cap lands inside it. Interior blanks
    are declined because stable packing would retime already-live rows against a
    different opponent index and market quote state.
    """
    limit = market_limit(configuration)
    report = {
        "schema_version": 2,
        "changed": False,
        "reason": "ineligible",
        "activation_class": None,
        "max_market_orders": limit,
        "blank_prefix_slots": [],
        "blocked_active_rows": [],
        "rescued_orders": [],
        "prefix_executable_before": 0,
        "prefix_executable_after": 0,
    }
    if not isinstance(action, dict):
        report["reason"] = "action_not_object"
        return action, report
    market = action.get("market")
    if not isinstance(market, list):
        report["reason"] = "market_not_list"
        return action, report

    prefix = market[:limit]
    blank_slots = [index for index, order in enumerate(prefix) if order == []]
    report["blank_prefix_slots"] = blank_slots
    report["market_length"] = len(market)
    report["prefix_executable_before"] = sum(is_engine_executable_order(order) for order in prefix)
    if not blank_slots:
        report["reason"] = "no_exact_blank_in_prefix"
        return action, report

    first_blank = blank_slots[0]
    blocked_active_rows = [
        {"from_index": index, "order": deepcopy(order)}
        for index, order in enumerate(prefix)
        if index > first_blank and order != []
    ]
    if blocked_active_rows:
        report["reason"] = "interior_blank_would_retime_active_order"
        report["blocked_active_rows"] = blocked_active_rows
        return action, report

    tagged = list(enumerate(market))
    packed = [entry for entry in tagged if entry[1] != []]
    packed.extend(entry for entry in tagged if entry[1] == [])
    rescued = [
        {"from_index": old_index, "to_index": new_index, "order": deepcopy(order)}
        for new_index, (old_index, order) in enumerate(packed[:limit])
        if old_index >= limit and is_engine_executable_order(order)
    ]
    if not rescued:
        report["reason"] = "no_executable_tail_order_crosses_cap"
        return action, report

    packed_market = [deepcopy(order) for _, order in packed]
    output = deepcopy(action)
    output["market"] = packed_market
    report.update(
        changed=True,
        reason="rescued_executable_tail_order",
        activation_class="suffix_only",
        rescued_orders=rescued,
        moved_blank_count=len(blank_slots),
        prefix_executable_after=sum(is_engine_executable_order(order) for order in packed_market[:limit]),
        market_sha256_before=_digest(market),
        market_sha256_after=_digest(packed_market),
    )
    return output, report
