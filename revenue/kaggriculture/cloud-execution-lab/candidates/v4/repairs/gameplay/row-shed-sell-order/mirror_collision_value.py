# SPDX-License-Identifier: Apache-2.0
"""Lockstep-correct mirror SELL queue evidence for canonical ROWSHED.

Research only.  For one product, a mirror baseline does *not* serialize our
whole lot before or after the rival's.  The official market interpreter quotes
both players from the same pre-commit inventory for each aligned unit, then
commits both quoted units.  Queue movement must therefore compare our serial
cash to that aligned baseline, not use the full early-minus-late span as a
symmetric assignment cost.

This module exposes that distinction and, for a unique-product SELL block,
solves the exact conditional permutation edge against a rival that keeps the
input baseline order.  It never chooses, mutates, or authorizes an action.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
SCHEMA = "titan.v4.rowshed.mirror-collision-value.v2"
ASSIGNMENT_SCHEMA = "titan.v4.rowshed.mirror-assignment.v2"
MAX_EXECUTABLE_UNITS_PER_MARKET_ORDER = 99_999
# Research certification bound only. maxMarketOrdersPerTurn defaults to 10 but
# custom configurations may be larger, so larger caller blocks remain score-
# only rather than being described as an engine horizon.
MAX_ASSIGNMENT_ROWS = 10


class MirrorCollisionInputError(ValueError):
    """Evidence is malformed or outside the certified mirror theorem."""


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


def _serial_sell_lot(
    price_fn: Callable[[str, int], Any], item: str, inventory: int, quantity: int
) -> tuple[int, int]:
    """Return cash and ending inventory when one player sells alone.

    Official commit semantics do not add public supply for a quote of exactly
    one coin, so floor-priced units leave inventory unchanged.
    """
    cash = 0
    level = inventory
    for _ in range(quantity):
        price = _quote(price_fn, item, level)
        cash += price
        if price != 1:
            level += 1
    return cash, level


def _aligned_mirror_lot(
    price_fn: Callable[[str, int], Any], item: str, inventory: int, quantity: int
) -> tuple[int, int]:
    """Return our cash and ending inventory for an aligned identical mirror row.

    In each official unit-loop iteration both players are quoted from the same
    pre-commit public inventory.  If the shared quote exceeds $1, both commits
    add one unit of supply; at the $1 floor neither commit advances inventory.
    """
    cash = 0
    level = inventory
    for _ in range(quantity):
        price = _quote(price_fn, item, level)
        cash += price
        if price != 1:
            level += 2
    return cash, level


def mirror_collision_score(
    *,
    item: str,
    public_inventory: int,
    fillable: int,
    price_fn: Callable[[str, int], Any],
) -> dict[str, Any]:
    """Return early/aligned/late cash and asymmetric queue-movement deltas.

    ``promote_gain`` is our gain from moving this unique-product row earlier
    than the rival's fixed baseline row. ``demote_loss`` is our loss from moving
    it later. ``serial_displacement_span`` is the old early-minus-late quantity
    retained only as a diagnostic; it is not a queue-assignment cost.
    """
    name = _item(item)
    level = _plain_nonnegative_int(public_inventory, "public_inventory")
    qty = _plain_positive_int(fillable, "fillable")
    if qty > MAX_EXECUTABLE_UNITS_PER_MARKET_ORDER:
        raise MirrorCollisionInputError("fillable exceeds official per-order unit-loop horizon")
    if not callable(price_fn):
        raise MirrorCollisionInputError("price_fn must be callable")

    early_cash, after_ours = _serial_sell_lot(price_fn, name, level, qty)
    aligned_cash, after_aligned = _aligned_mirror_lot(price_fn, name, level, qty)
    _rival_cash, after_rival = _serial_sell_lot(price_fn, name, level, qty)
    late_cash, after_both_serial = _serial_sell_lot(
        price_fn, name, after_rival, qty
    )

    promote_gain = early_cash - aligned_cash
    demote_loss = aligned_cash - late_cash
    serial_span = early_cash - late_cash
    if min(promote_gain, demote_loss, serial_span) < 0:
        raise MirrorCollisionInputError("mirror price path is not monotone nonincreasing")
    if promote_gain + demote_loss != serial_span:
        raise MirrorCollisionInputError("mirror cash decomposition is inconsistent")

    before = _quote(price_fn, name, level)
    endpoint_after = _quote(price_fn, name, level + qty)
    incumbent_endpoint_score = (before - endpoint_after) * qty
    return {
        "item": name,
        "public_inventory": level,
        "fillable": qty,
        "early_cash": early_cash,
        "aligned_mirror_cash": aligned_cash,
        "late_cash": late_cash,
        "promote_gain": promote_gain,
        "demote_loss": demote_loss,
        "serial_displacement_span": serial_span,
        "serial_displacement_is_assignment_cost": False,
        "incumbent_endpoint_score": incumbent_endpoint_score,
        "after_our_lot_inventory": after_ours,
        "after_aligned_mirror_inventory": after_aligned,
        "after_both_serial_inventory": after_both_serial,
    }


def _assignment_deltas(rows: Sequence[Any]) -> list[tuple[int, int]]:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise MirrorCollisionInputError("assignment rows must be a sequence")
    if len(rows) > MAX_ASSIGNMENT_ROWS:
        raise MirrorCollisionInputError("assignment row count exceeds research safety bound")
    out: list[tuple[int, int]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise MirrorCollisionInputError(f"assignment row {index} must be a mapping")
        promote = _plain_nonnegative_int(row.get("promote_gain"), f"promote gain {index}")
        demote = _plain_nonnegative_int(row.get("demote_loss"), f"demote loss {index}")
        out.append((promote, demote))
    return out


def mirror_edge_for_permutation(
    rows: Sequence[Any], permutation: Sequence[Any]
) -> int:
    """Exact conditional cash delta vs a rival retaining original row order."""
    deltas = _assignment_deltas(rows)
    if not isinstance(permutation, Sequence) or isinstance(permutation, (str, bytes)):
        raise MirrorCollisionInputError("permutation must be a sequence")
    order: list[int] = []
    for index, value in enumerate(permutation):
        if type(value) is not int:
            raise MirrorCollisionInputError(f"permutation index {index} must be a plain int")
        order.append(value)
    if sorted(order) != list(range(len(deltas))):
        raise MirrorCollisionInputError("permutation must contain each row index exactly once")

    candidate_position = [0] * len(deltas)
    for position, original_index in enumerate(order):
        candidate_position[original_index] = position

    total = 0
    for original_index, (promote_gain, demote_loss) in enumerate(deltas):
        position = candidate_position[original_index]
        if position < original_index:
            total += promote_gain
        elif position > original_index:
            total -= demote_loss
    return total


def optimal_mirror_assignment(rows: Sequence[Any]) -> tuple[list[int], int]:
    """Exact O(n*2^n) assignment for the <=10 unique-product theorem."""
    deltas = _assignment_deltas(rows)
    n = len(deltas)
    if n < 2:
        return list(range(n)), 0

    states: dict[int, tuple[int, int, tuple[int, ...]]] = {0: (0, 0, ())}
    for mask in range(1 << n):
        state = states.get(mask)
        if state is None:
            continue
        score, moved, prefix = state
        position = len(prefix)
        for original_index, (promote_gain, demote_loss) in enumerate(deltas):
            bit = 1 << original_index
            if mask & bit:
                continue
            delta = 0
            if position < original_index:
                delta = promote_gain
            elif position > original_index:
                delta = -demote_loss
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
            "rival retains the same unique-product SELL rows at the input baseline indices"
        ),
        "objective": (
            "+promote_gain when earlier, -demote_loss when later, 0 when aligned"
        ),
        "optimal_permutation_indices": None,
        "predicted_mirror_edge": None,
    }
    if len(scored) > MAX_ASSIGNMENT_ROWS:
        report["reason"] = "row_count_exceeds_assignment_safety_bound"
        return report
    if len(set(items)) != len(items):
        report["reason"] = "duplicate_product_rows_require_full_market_simulation"
        return report

    permutation, edge = optimal_mirror_assignment(scored)
    report.update(
        certified=True,
        reason="unique_product_lockstep_baseline_assignment",
        movement_deltas=[
            {
                "original_index": row["original_index"],
                "promote_gain": row["promote_gain"],
                "demote_loss": row["demote_loss"],
            }
            for row in scored
        ],
        optimal_permutation_indices=permutation,
        predicted_mirror_edge=edge,
    )
    return report


def analyze_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    price_fn: Callable[[str, int], Any],
) -> dict[str, Any]:
    """Score executable SELL evidence and certify a unique-product assignment."""
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
    serial_span_rank = [
        row["original_index"]
        for row in sorted(
            scored,
            key=lambda row: (-row["serial_displacement_span"], row["original_index"]),
        )
    ]
    assignment = _assignment_report(scored)
    if assignment["certified"]:
        assignment["serial_span_rank_indices"] = serial_span_rank
        assignment["serial_span_rank_predicted_edge"] = mirror_edge_for_permutation(
            scored, serial_span_rank
        )
        assignment["serial_span_rank_is_optimal"] = (
            serial_span_rank == assignment["optimal_permutation_indices"]
        )

    return {
        "schema": SCHEMA,
        "engine_git_blob": ENGINE_GIT_BLOB,
        "research_only": True,
        "decision_authority": False,
        "action_mutation_authority": False,
        "rival_action_prediction": False,
        "conditional_assumption": (
            "rival retains identical unique-product item+quantity rows at baseline indices"
        ),
        "scores": scored,
        "incumbent_rank_indices": incumbent_rank,
        "serial_span_rank_indices": serial_span_rank,
        "serial_span_rank_semantics": (
            "descending early-minus-late diagnostic only; not an assignment objective"
        ),
        "rank_diverges": incumbent_rank != serial_span_rank,
        "mirror_assignment": assignment,
    }
