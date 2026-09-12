# SPDX-License-Identifier: Apache-2.0
"""Exact mirror SELL queue-index value evidence for canonical ROWSHED.

Research only.  The incumbent ROWSHED donor ranks executable SELL rows with an
endpoint price-drop heuristic.  Against a mirror/copy opponent that sells the
same product and quantity, the official per-unit lockstep interpreter gives a
sharper quantity: the cash advantage of selling that lot before, rather than
after, the rival's identical lot.

This module computes that quantity and, for a unique-product executable SELL
block, the exact permutation that maximizes the conditional mirror edge.  It
does not choose, mutate, or authorize an action.  Callers must provide the
authenticated official ``market_price`` function (the focused tests use the
source-bound V4 market baseline).
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
SCHEMA = "titan.v4.rowshed.mirror-collision-value.v1"
ASSIGNMENT_SCHEMA = "titan.v4.rowshed.mirror-assignment.v1"
# Official _process_market aborts a unit loop before iteration 100_000.
MAX_EXECUTABLE_UNITS_PER_MARKET_ORDER = 99_999
# Official maxMarketOrdersPerTurn defaults to 10; assignment evidence never
# certifies a larger block even if a caller supplies one.
MAX_ASSIGNMENT_ROWS = 10


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


def _assignment_costs(costs: Sequence[Any]) -> list[int]:
    if not isinstance(costs, Sequence) or isinstance(costs, (str, bytes)):
        raise MirrorCollisionInputError("assignment costs must be a sequence")
    if len(costs) > MAX_ASSIGNMENT_ROWS:
        raise MirrorCollisionInputError("assignment row count exceeds official market horizon")
    return [
        _plain_nonnegative_int(value, f"assignment cost {index}")
        for index, value in enumerate(costs)
    ]


def mirror_edge_for_permutation(
    costs: Sequence[Any], permutation: Sequence[Any]
) -> int:
    """Return the exact conditional mirror edge of one row permutation.

    `costs[i]` is row i's exact mirror collision value.  For unique products,
    moving row i before the rival mirror's baseline position earns +cost; moving
    it after pays -cost; staying at the same raw index contributes zero.
    """
    values = _assignment_costs(costs)
    if not isinstance(permutation, Sequence) or isinstance(permutation, (str, bytes)):
        raise MirrorCollisionInputError("permutation must be a sequence")
    order = []
    for index, value in enumerate(permutation):
        if type(value) is not int:
            raise MirrorCollisionInputError(f"permutation index {index} must be a plain int")
        order.append(value)
    if sorted(order) != list(range(len(values))):
        raise MirrorCollisionInputError("permutation must contain each row index exactly once")
    candidate_position = [0] * len(values)
    for position, original_index in enumerate(order):
        candidate_position[original_index] = position
    total = 0
    for original_index, cost in enumerate(values):
        position = candidate_position[original_index]
        if position < original_index:
            total += cost
        elif position > original_index:
            total -= cost
    return total


def optimal_mirror_assignment(costs: Sequence[Any]) -> tuple[list[int], int]:
    """Exact O(n*2^n) assignment for the <=10-row unique-product theorem.

    Ties prefer fewer moved rows, then lexicographically smaller original-index
    permutations, so identity is retained when no positive edge exists.
    """
    values = _assignment_costs(costs)
    n = len(values)
    if n < 2:
        return list(range(n)), 0

    # mask -> (score, moved_count, original-index permutation prefix)
    states: dict[int, tuple[int, int, tuple[int, ...]]] = {0: (0, 0, ())}
    for mask in range(1 << n):
        state = states.get(mask)
        if state is None:
            continue
        score, moved, prefix = state
        position = len(prefix)
        for original_index in range(n):
            bit = 1 << original_index
            if mask & bit:
                continue
            delta = 0
            if position < original_index:
                delta = values[original_index]
            elif position > original_index:
                delta = -values[original_index]
            candidate = (
                score + delta,
                moved + (position != original_index),
                prefix + (original_index,),
            )
            next_mask = mask | bit
            incumbent = states.get(next_mask)
            if incumbent is None or (
                candidate[0], -candidate[1], tuple(-x for x in candidate[2])
            ) > (
                incumbent[0], -incumbent[1], tuple(-x for x in incumbent[2])
            ):
                states[next_mask] = candidate

    score, _moved, permutation = states[(1 << n) - 1]
    if score <= 0:
        return list(range(n)), 0
    return list(permutation), score


def _assignment_report(scored: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    items = [row["item"] for row in scored]
    report: dict[str, Any] = {
        "schema": ASSIGNMENT_SCHEMA,
        "certified": False,
        "conditional_assumption": (
            "rival submits the same unique-product SELL rows at the input baseline indices"
        ),
        "objective": "+collision value when earlier, -collision value when later, 0 when same",
        "optimal_permutation_indices": None,
        "predicted_mirror_edge": None,
    }
    if len(scored) > MAX_ASSIGNMENT_ROWS:
        report["reason"] = "row_count_exceeds_official_market_horizon"
        return report
    if len(set(items)) != len(items):
        report["reason"] = "duplicate_product_rows_outside_assignment_theorem"
        return report
    costs = [row["exact_mirror_collision_value"] for row in scored]
    permutation, edge = optimal_mirror_assignment(costs)
    report.update(
        certified=True,
        reason="unique_product_exact_assignment",
        costs=costs,
        optimal_permutation_indices=permutation,
        predicted_mirror_edge=edge,
    )
    return report


def analyze_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    price_fn: Callable[[str, int], Any],
) -> dict[str, Any]:
    """Score caller-authenticated executable SELL evidence under both metrics.

    Each row must contain exactly ``item``, ``public_inventory`` and ``fillable``.
    Stable score ties preserve caller order.  ``mirror_rank_indices`` remains a
    descending score view for compatibility; it is explicitly NOT a queue
    optimum.  Unique-product blocks additionally receive an exact assignment
    certificate.  The report is evidence only and never returns an action.
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
    assignment = _assignment_report(scored)
    if assignment["certified"]:
        costs = assignment["costs"]
        assignment["descending_score_permutation_indices"] = mirror_rank
        assignment["descending_score_predicted_edge"] = mirror_edge_for_permutation(
            costs, mirror_rank
        )
        assignment["descending_score_is_optimal"] = (
            mirror_rank == assignment["optimal_permutation_indices"]
        )

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
        "mirror_rank_semantics": "descending per-row evidence only; not queue-optimal assignment",
        "rank_diverges": incumbent_rank != mirror_rank,
        "mirror_assignment": assignment,
    }
