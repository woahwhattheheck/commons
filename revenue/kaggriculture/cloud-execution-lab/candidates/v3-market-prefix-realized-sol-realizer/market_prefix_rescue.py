# SPDX-License-Identifier: Apache-2.0
"""Stable market-prefix transport repair for TITAN V3.

The pinned Kaggriculture interpreter slices the raw market queue to
``maxMarketOrdersPerTurn`` before parsing each row. An exact ``[]`` inside that
prefix therefore consumes a transport slot even though it is a no-op. This
module moves only exact blank rows, preserves every non-blank value and relative
order, and commits the edit only when every row newly exposed to the interpreter
is structurally executable and at least one executable tail order crosses the
raw cap.

"Structurally executable" deliberately does not mean "realized". Affordability,
stock, shed capacity, and all other live preconditions remain engine decisions.
The evidence carrier measures post-interpreter state separately.

Mechanism and original implementation credit: Commons PR #11616. This version
is a fresh-current-main rebuild with fail-closed configuration, transport, and
diagnostic handling plus separate realized-execution custody.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping, Optional

CROPS = frozenset({"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"})
ANIMALS = frozenset({"GOOSE", "COW", "SHEEP"})
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
QUANTITY_OPS = frozenset({"BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"})
ATOMIC_OPS = frozenset({"HIRE", "BUY_LAND"})
SCHEMA = "titan-market-prefix-rescue/v2"


def _config_value(configuration: Any, key: str, default: Any) -> Any:
    if configuration is None:
        return default
    if isinstance(configuration, Mapping):
        return configuration.get(key, default)
    return getattr(configuration, key, default)


def market_limit(configuration: Any = None) -> Optional[int]:
    """Return the exact lower-bounded engine cap, or ``None`` on invalid input.

    Missing configuration uses the official default. Malformed explicit values
    decline the transformation rather than silently inventing a cap.
    """

    try:
        return max(1, int(_config_value(configuration, "maxMarketOrdersPerTurn", 10)))
    except (TypeError, ValueError, OverflowError):
        return None


def is_structurally_executable_order(order: Any) -> bool:
    """Return whether a row can reach a pinned-engine market operation handler.

    The predicate is total for JSON-shaped values. In particular, list/dict
    operation or item tokens and non-finite quantities return ``False`` instead
    of escaping from set membership or integer conversion.
    """

    if not isinstance(order, list) or not order:
        return False
    op = order[0]
    if not isinstance(op, str):
        return False
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
    item = order[1]
    if not isinstance(item, str):
        return False
    if op == "BUY_SEED":
        return item in CROPS
    if op == "BUY_ANIMAL":
        return item in ANIMALS
    if op == "BUY_PRODUCT":
        return item in {"WHEAT", "FERTILIZER"}
    return item in PRODUCTS


def _digest(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _strict_digest_or_none(value: Any) -> Optional[str]:
    """Return a strict-JSON digest or ``None`` without risking agent failure."""

    try:
        return _digest(value)
    except (TypeError, ValueError, OverflowError, RecursionError):
        return None


def rescue_market_prefix(action: Any, configuration: Any = None):
    """Return ``(action_or_copy, report)`` after one narrow stable packing.

    The input is never mutated. No order is added, removed, edited, or reordered
    relative to another non-blank order. Exact blank rows move only when at
    least one structurally executable order originally outside the raw cap lands
    inside it, and every row newly entering that prefix is structurally
    executable. Any uncertain transport or receipt returns the inherited action
    object unchanged.
    """

    limit = market_limit(configuration)
    report = {
        "schema": SCHEMA,
        "syntactic_changed": False,
        "reason": "ineligible",
        "max_market_orders": limit,
        "blank_prefix_slots": [],
        "crossings": [],
        "prefix_structural_before": 0,
        "prefix_structural_after": 0,
        "newly_exposed_rows": [],
        "nonstructural_newly_exposed_rows": [],
    }
    if limit is None:
        report["reason"] = "invalid_market_limit"
        return action, report
    if not isinstance(action, dict):
        report["reason"] = "action_not_object"
        return action, report
    market = action.get("market")
    if not isinstance(market, list):
        report["reason"] = "market_not_list"
        return action, report

    prefix = market[:limit]
    blanks = [index for index, row in enumerate(prefix) if row == []]
    report["blank_prefix_slots"] = blanks
    report["market_length"] = len(market)
    report["prefix_structural_before"] = sum(
        is_structurally_executable_order(row) for row in prefix
    )
    if not blanks:
        report["reason"] = "no_exact_blank_in_prefix"
        return action, report

    tagged = list(enumerate(market))
    packed = [entry for entry in tagged if entry[1] != []]
    packed.extend(entry for entry in tagged if entry[1] == [])

    newly_exposed = [
        (new_index, old_index, row)
        for new_index, (old_index, row) in enumerate(packed[:limit])
        if old_index >= limit
    ]
    report["newly_exposed_rows"] = [
        {"from_index": old_index, "to_index": new_index}
        for new_index, old_index, _ in newly_exposed
    ]

    crossing_entries = [
        (new_index, old_index, row)
        for new_index, old_index, row in newly_exposed
        if is_structurally_executable_order(row)
    ]
    if not crossing_entries:
        report["reason"] = "no_structural_tail_order_crosses_cap"
        return action, report

    nonstructural = [
        {"from_index": old_index, "to_index": new_index}
        for new_index, old_index, row in newly_exposed
        if not is_structurally_executable_order(row)
    ]
    if nonstructural:
        report["reason"] = "nonstructural_tail_order_would_enter_prefix"
        report["nonstructural_newly_exposed_rows"] = nonstructural
        return action, report

    try:
        packed_market = [deepcopy(row) for _, row in packed]
    except Exception:
        report["reason"] = "market_copy_failed"
        return action, report

    before_digest = _strict_digest_or_none(market)
    after_digest = _strict_digest_or_none(packed_market)
    if before_digest is None or after_digest is None:
        report["reason"] = "diagnostic_digest_unsafe"
        return action, report
    if before_digest == after_digest:
        report["reason"] = "no_market_byte_change"
        return action, report

    try:
        output = deepcopy(action)
    except Exception:
        report["reason"] = "action_copy_failed"
        return action, report
    output["market"] = packed_market
    crossings = [
        {
            "from_index": old_index,
            "to_index": new_index,
            "order": deepcopy(row),
        }
        for new_index, old_index, row in crossing_entries
    ]
    report.update(
        syntactic_changed=True,
        reason="structural_tail_order_crossed_cap",
        crossings=crossings,
        moved_blank_count=len(blanks),
        prefix_structural_after=sum(
            is_structurally_executable_order(row) for row in packed_market[:limit]
        ),
        market_sha256_before=before_digest,
        market_sha256_after=after_digest,
    )
    return output, report
