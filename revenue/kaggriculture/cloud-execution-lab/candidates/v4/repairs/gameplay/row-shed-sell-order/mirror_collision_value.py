# SPDX-License-Identifier: Apache-2.0
"""Exact mirror SELL queue-index value evidence for canonical ROWSHED.

Research only.  The incumbent ROWSHED donor ranks executable SELL rows with an
endpoint price-drop heuristic.  Against a mirror/copy opponent that sells the
same product and quantity, the official per-unit lockstep interpreter gives a
sharper quantity: the cash advantage of selling that lot before, rather than
after, the rival's identical lot.

This module computes that quantity without choosing, mutating, or authorizing an
action.  Callers must provide the authenticated official ``market_price``
function (the focused tests use the source-bound V4 market baseline).
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
SCHEMA = "titan.v4.rowshed.mirror-collision-value.v1"
# Official _process_market aborts a unit loop before iteration 100_000.
MAX_EXECUTABLE_UNITS_PER_MARKET_ORDER = 99_999


class MirrorCollisionInputError(ValueError):
    """Evidence is malformed or cannot support a mirror-collision score."""


def _plain_nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise MirrorCollisionInputError(f"{label} must be a plain nonnegative int")
    return value


def _plain_positive_int(value: Any, label: str) -> int:
    value = _plain_nonnegative_int(value, label)
    if value == 0:
        raise MirrorCollisionInputError(f"{label} must be positive")
    return value


def _item(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise MirrorCollisionInputError("item must be a nonempty string")
    return value


def _quote(price_fn: Callable[[str, int], Any], item: str, inventory: int) -> int:
    try:
        price = price_fn(item, inventory)
    except (KeyError, ValueError, TypeError, OverflowError) as error:
        raise MirrorCollisionInputError("price function rejected evidence") from error
    if type(price) is not int or price < 1:
        raise MirrorCollisionInputError("price must be a plain positive int")
    return price


def _sell_lot(
    price_fn: Callable[[str, int], Any], item: str, inventory: int, quantity: int
) -> tuple[int, int]:
    """Return (cash, ending inventory) for one SELL lot.

    Official ``_commit_unit`` does not add market supply for a $1 sale.  Keeping
    that detail here matters in deep-glut tails and avoids pretending every sale
    advances inventory by one.
    """
    cash = 0
    level = inventory
    for _ in range(quantity):
        price = _quote(price_fn, item, level)
        cash += price
        if price != 1:
            level += 1
    return cash, level


def mirror_collision_score(
    *,
    item: str,
    public_inventory: int,
    fillable: int,
    price_fn: Callable[[str, int], Any],
) -> dict[str, Any]:
    """Compare our cash when an identical rival lot is later vs earlier.

    This is a conditional mirror-race value, not a rival-action prediction.  It
    assumes the rival sells the same item and executable quantity once in the
    competing queue slot; it says nothing about whether that event will occur.
    """
    name = _item(item)
    level = _plain_nonnegative_int(public_inventory, "public_inventory")
    qty = _plain_positive_int(fillable, "fillable")
    if qty > MAX_EXECUTABLE_UNITS_PER_MARKET_ORDER:
        raise MirrorCollisionInputError("fillable exceeds official per-order unit-loop horizon")
    if not callable(price_fn):
        raise MirrorCollisionInputError("price_fn must be callable")

    early_cash, after_ours = _sell_lot(price_fn, name, level, qty)
    _rival_cash, after_rival = _sell_lot(price_fn, name, level, qty)
    late_cash, _after_both = _sell_lot(price_fn, name, after_rival, qty)

    before = _quote(price_fn, name, level)
    endpoint_after = _quote(price_fn, name, level + qty)
    incumbent_endpoint_score = (before - endpoint_after) * qty
    exact_collision_value = early_cash - late_cash
    if exact_collision_value < 0:
        raise MirrorCollisionInputError("monotone mirror collision value became negative")

    return {
        "item": name,
        "public_inventory": level,
        "fillable": qty,
        "early_cash": early_cash,
        "late_cash": late_cash,
        "exact_mirror_collision_value": exact_collision_value,
        "incumbent_endpoint_score": incumbent_endpoint_score,
        "after_our_lot_inventory": after_ours,
    }


def analyze_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    price_fn: Callable[[str, int], Any],
) -> dict[str, Any]:
    """Rank caller-authenticated executable SELL evidence under both metrics.

    Each row must contain exactly ``item``, ``public_inventory`` and ``fillable``.
    Stable ties preserve caller order.  The report is evidence only; it never
    returns a transformed market queue.
    """
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise MirrorCollisionInputError("rows must be a sequence")
    if len(rows) < 2:
        raise MirrorCollisionInputError("at least two rows are required")

    scored: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise MirrorCollisionInputError("row must be a mapping")
        if set(row) != {"item", "public_inventory", "fillable"}:
            raise MirrorCollisionInputError("row key set drift")
        score = mirror_collision_score(
            item=row.get("item"),
            public_inventory=row.get("public_inventory"),
            fillable=row.get("fillable"),
            price_fn=price_fn,
        )
        score["original_index"] = index
        scored.append(score)

    incumbent_rank = [
        row["original_index"]
        for row in sorted(
            scored,
            key=lambda row: (-row["incumbent_endpoint_score"], row["original_index"]),
        )
    ]
    mirror_rank = [
        row["original_index"]
        for row in sorted(
            scored,
            key=lambda row: (-row["exact_mirror_collision_value"], row["original_index"]),
        )
    ]
    return {
        "schema": SCHEMA,
        "engine_git_blob": ENGINE_GIT_BLOB,
        "research_only": True,
        "decision_authority": False,
        "action_mutation_authority": False,
        "rival_action_prediction": False,
        "conditional_assumption": "rival sells identical item+quantity in competing queue slot",
        "scores": scored,
        "incumbent_rank_indices": incumbent_rank,
        "mirror_rank_indices": mirror_rank,
        "rank_diverges": incumbent_rank != mirror_rank,
    }
