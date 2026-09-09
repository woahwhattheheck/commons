# SPDX-License-Identifier: Apache-2.0
"""Executable-slot model for the frozen Titan V2 seller queue.

The official interpreter executes only the first ``maxMarketOrdersPerTurn``
rows and treats a falsy row as a no-op.  Frozen V2 instead used the raw Python
list length as its capacity certificate.  These helpers encode both rules and
produce a deterministic predecessor-failing witness.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Sequence

OPERATION = "titan-v2-market-hole-capacity-20260909-sol-parapet-01"
DEFAULT_LIMIT = 10


class SlotCapacityError(ValueError):
    """The queue or requested placement is malformed or not executable."""


def _quantity(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SlotCapacityError(f"{label} must be a non-negative integer")
    return value


def _limit(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SlotCapacityError("limit must be a positive integer")
    return value


def active_prefix(orders: Sequence[Any], limit: int = DEFAULT_LIMIT) -> list[Any]:
    """Return the exact market rows the official interpreter can inspect."""
    return list(orders[: _limit(limit)])


def first_executable_hole(
    orders: Sequence[Any], limit: int = DEFAULT_LIMIT
) -> int | None:
    """Return the first falsy row in the interpreter-visible prefix."""
    for index, order in enumerate(active_prefix(orders, limit)):
        if not order:
            return index
    return None


def offered_quantity(
    orders: Sequence[Any], item: str, *, limit: int | None = None
) -> int:
    """Sum same-item SELL quantity, optionally over only executable rows."""
    if not isinstance(item, str) or not item:
        raise SlotCapacityError("item must be a non-empty string")
    selected = orders if limit is None else active_prefix(orders, limit)
    total = 0
    for order in selected:
        if (
            order
            and isinstance(order, (list, tuple))
            and len(order) > 2
            and order[0] == "SELL"
            and order[1] == item
        ):
            total += max(0, _quantity(order[2], f"{item} offered quantity"))
    return total


def legacy_can_schedule(
    orders: Sequence[Any], item: str, quantity: int, limit: int = DEFAULT_LIMIT
) -> bool:
    """Frozen V2's raw-list-length capacity predicate."""
    quantity = _quantity(quantity, "quantity")
    limit = _limit(limit)
    if len(orders) >= limit and quantity > offered_quantity(orders, item):
        return False
    return True


def executable_can_schedule(
    orders: Sequence[Any], item: str, quantity: int, limit: int = DEFAULT_LIMIT
) -> bool:
    """Admit only when inherited slots or a real executable hole can carry it."""
    quantity = _quantity(quantity, "quantity")
    limit = _limit(limit)
    if quantity <= offered_quantity(orders, item, limit=limit):
        return True
    if len(orders) < limit:
        return True
    return first_executable_hole(orders, limit) is not None


def place_additional_sale(
    orders: Sequence[Any], item: str, quantity: int, limit: int = DEFAULT_LIMIT
) -> tuple[list[Any], int | None]:
    """Place one new SELL without moving any inherited live row.

    A falsy row in the active prefix is replaced in place.  Otherwise the sale
    is appended only when the raw list is shorter than the execution limit.
    The input sequence is never mutated.
    """
    quantity = _quantity(quantity, "quantity")
    limit = _limit(limit)
    copied = copy.deepcopy(list(orders))
    if quantity == 0:
        return copied, None
    hole = first_executable_hole(copied, limit)
    if hole is not None:
        copied[hole] = ["SELL", item, quantity]
        return copied, hole
    if len(copied) < limit:
        copied.append(["SELL", item, quantity])
        return copied, len(copied) - 1
    return copied, None


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def witness() -> dict[str, Any]:
    """Construct the exact false-full queue and two rejecting controls."""
    live = [
        ["BUY_LAND"],
        ["BUY_SEED", "WHEAT", 1],
        ["BUY_ANIMAL", "GOOSE", 1],
        ["SELL", "MILK", 2],
        [],
        ["BUY_PRODUCT", "WHEAT", 1],
        ["SELL", "EGG", 1],
        ["BUY_SEED", "CARROT", 1],
        ["HIRE"],
        ["SELL", "FERTILIZER", 1],
    ]
    item, quantity, limit = "CARROT", 4, DEFAULT_LIMIT
    before = copy.deepcopy(live)
    placed, index = place_additional_sale(before, item, quantity, limit)

    if legacy_can_schedule(before, item, quantity, limit):
        raise SlotCapacityError("predecessor unexpectedly admits the false-full witness")
    if not executable_can_schedule(before, item, quantity, limit):
        raise SlotCapacityError("candidate unexpectedly rejects an executable hole")
    if index != 4 or placed[index] != ["SELL", item, quantity]:
        raise SlotCapacityError("candidate did not consume the first active-prefix hole")
    for row_index, row in enumerate(before):
        if row_index == index:
            continue
        if placed[row_index] != row:
            raise SlotCapacityError(f"live row moved or changed at index {row_index}")
    if len(placed) != len(before):
        raise SlotCapacityError("hole reuse changed queue length")

    full = copy.deepcopy(before)
    full[4] = ["SELL", "WOOL", 1]
    if executable_can_schedule(full, item, quantity, limit):
        raise SlotCapacityError("candidate admits a genuinely full active prefix")
    rejected, rejected_index = place_additional_sale(full, item, quantity, limit)
    if rejected_index is not None or rejected != full:
        raise SlotCapacityError("candidate mutated a genuinely full queue")

    suffix_hole = copy.deepcopy(full) + [[]]
    if executable_can_schedule(suffix_hole, item, quantity, limit):
        raise SlotCapacityError("candidate treats an inactive suffix hole as capacity")

    return {
        "schema_version": 1,
        "operation": OPERATION,
        "verdict": "PREDECESSOR_FALSE_FULL_CONFIRMED",
        "limit": limit,
        "item": item,
        "quantity": quantity,
        "predecessor": {
            "raw_rows": len(before),
            "active_live_rows": sum(bool(row) for row in active_prefix(before, limit)),
            "first_hole": first_executable_hole(before, limit),
            "can_schedule": legacy_can_schedule(before, item, quantity, limit),
        },
        "candidate": {
            "can_schedule": executable_can_schedule(before, item, quantity, limit),
            "placed_index": index,
            "raw_rows": len(placed),
            "active_live_rows": sum(bool(row) for row in active_prefix(placed, limit)),
            "live_rows_preserved_by_index": True,
            "queue_sha256": hashlib.sha256(_canonical(placed)).hexdigest(),
        },
        "controls": {
            "full_prefix_rejected": not executable_can_schedule(
                full, item, quantity, limit
            ),
            "suffix_only_hole_rejected": not executable_can_schedule(
                suffix_hole, item, quantity, limit
            ),
            "active_same_item_covered_without_new_slot": executable_can_schedule(
                [*full[:4], ["SELL", item, quantity], *full[5:]],
                item,
                quantity,
                limit,
            ),
            "inactive_same_item_not_counted": not executable_can_schedule(
                full + [["SELL", item, quantity]], item, quantity, limit
            ),
        },
    }


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = witness()
    payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    atomic_write(args.output, payload.encode("utf-8"))
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
