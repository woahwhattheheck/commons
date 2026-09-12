#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact mirror-queue competition oracle for TITAN V4 market SELL rows.

Research-only.  This module models the public, official per-unit lockstep market
semantics for SELL rows and answers a narrow question: if an opponent submits the
same unique-product SELL block as our incumbent queue, what permutation of OUR
same rows maximizes the one-callback revenue edge?

It does not observe rival current actions, alter runtime defaults, or authorize a
controller change.  The mirror assumption must be established by separate
hosted/replay evidence before any gameplay use.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import itertools
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Sequence


class EvidenceError(ValueError):
    """Inputs cannot support the stated mirror-queue theorem."""


HERE = Path(__file__).resolve().parent
LAB_ROOT = HERE.parents[3]
MECHANICS_PATH = LAB_ROOT / "mechanics.py"
# Exact main@9d3f32a... mechanics.py Git blob, itself mechanically extracted
# from the pinned public engine.  CLI evidence fails closed on byte drift.
MECHANICS_GIT_BLOB = "044a4f9c0a4a44dde10ada57563238bcaf82075d"


def _git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def load_pinned_mechanics(path: Path | None = None) -> ModuleType:
    """Load mechanics from one captured, authenticated byte buffer."""
    source = MECHANICS_PATH if path is None else Path(path)
    data = source.read_bytes()
    actual = _git_blob(data)
    if actual != MECHANICS_GIT_BLOB:
        raise EvidenceError(
            f"mechanics blob mismatch: expected {MECHANICS_GIT_BLOB}, got {actual}"
        )
    module = ModuleType("titan_v4_sell_queue_pinned_mechanics")
    module.__file__ = str(source)
    exec(compile(data, str(source), "exec"), module.__dict__)
    for name in ("market_price", "MARKET_PARAMS", "PRICE_FLOOR"):
        if not hasattr(module, name):
            raise EvidenceError(f"pinned mechanics missing {name}")
    return module


def _plain_int(value: Any, label: str, *, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise EvidenceError(f"{label} must be a literal integer")
    if minimum is not None and value < minimum:
        raise EvidenceError(f"{label} must be >= {minimum}")
    return value


def sale_revenue(model: Any, item: str, inventory: int, units: int, params=None) -> tuple[int, int]:
    """Exact SELL revenue and final inventory for one uninterrupted order.

    This mirrors official `_process_market` + `_commit_unit`: each unit is quoted
    from current public inventory, and a $1 sale does not add market supply.
    """
    inventory = _plain_int(inventory, "inventory")
    units = _plain_int(units, "units", minimum=0)
    revenue = 0
    level = inventory
    for _ in range(units):
        price = model.market_price(item, level, params)
        if type(price) is not int or price < 1:
            raise EvidenceError("market price must be a positive literal integer")
        revenue += price
        if price > 1:
            level += 1
    return revenue, level


def mirror_displacement_cost(model: Any, item: str, inventory: int, units: int, params=None) -> int:
    """Revenue advantage of selling `item` before an equal mirror SELL order."""
    first, after_first = sale_revenue(model, item, inventory, units, params)
    second, _ = sale_revenue(model, item, after_first, units, params)
    return first - second


def endpoint_proxy_cost(model: Any, item: str, inventory: int, units: int, params=None) -> int:
    """The historical ROWSHED endpoint-drop proxy, retained only for comparison."""
    inventory = _plain_int(inventory, "inventory")
    units = _plain_int(units, "units", minimum=0)
    before = model.market_price(item, inventory, params)
    after = model.market_price(item, inventory + units, params)
    if type(before) is not int or type(after) is not int:
        raise EvidenceError("market price must be a literal integer")
    return (before - after) * units


def _leading_unique_sell_block(
    rows: Any,
    market_inventory: Any,
    shed: Any,
    *,
    max_orders: int = 10,
) -> tuple[int, list[dict[str, Any]]]:
    if not isinstance(rows, list):
        raise EvidenceError("market rows must be a list")
    if not isinstance(market_inventory, dict):
        raise EvidenceError("market inventory must be a dict")
    if not isinstance(shed, dict):
        raise EvidenceError("shed must be a dict")
    max_orders = _plain_int(max_orders, "max_orders", minimum=1)

    limit = min(len(rows), max_orders)
    block: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index in range(limit):
        row = rows[index]
        if not row:
            break
        if not isinstance(row, list):
            raise EvidenceError(f"executable row {index} must be a list")
        if not row or row[0] != "SELL":
            break
        if len(row) < 3:
            raise EvidenceError(f"SELL row {index} is missing item/quantity")
        item = row[1]
        requested = row[2]
        if not isinstance(item, str) or not item:
            raise EvidenceError(f"SELL row {index} item must be a nonempty string")
        requested = _plain_int(requested, f"SELL row {index} quantity", minimum=1)
        if item in seen:
            raise EvidenceError("duplicate product in leading SELL block is outside theorem")
        seen.add(item)
        if item not in market_inventory:
            raise EvidenceError(f"market inventory missing {item}")
        level = _plain_int(market_inventory[item], f"market inventory {item}")
        if item not in shed:
            raise EvidenceError(f"shed missing {item}")
        stock = _plain_int(shed[item], f"shed {item}", minimum=0)
        fill = min(requested, stock)
        block.append(
            {
                "original_index": index,
                "row": deepcopy(row),
                "item": item,
                "requested": requested,
                "stock": stock,
                "fill": fill,
                "inventory": level,
            }
        )
    return limit, block


def _edge_contribution(cost: int, original_index: int, candidate_index: int) -> int:
    if candidate_index < original_index:
        return cost
    if candidate_index > original_index:
        return -cost
    return 0


def edge_for_indices(costs: Sequence[int], candidate_indices: Sequence[int]) -> int:
    """Mirror edge implied by moving original rows into candidate positions."""
    n = len(costs)
    if sorted(candidate_indices) != list(range(n)):
        raise EvidenceError("candidate_indices must be a permutation")
    candidate_pos = [0] * n
    for position, original_index in enumerate(candidate_indices):
        candidate_pos[original_index] = position
    return sum(
        _edge_contribution(int(costs[i]), i, candidate_pos[i]) for i in range(n)
    )


def optimal_indices(costs: Sequence[int]) -> tuple[list[int], int]:
    """Exact O(n*2^n) mirror assignment for <=10 market slots.

    State tie-breaks prefer fewer moved rows, then lexicographically smaller
    original indices.  This keeps identity when there is no positive edge.
    """
    costs = [int(value) for value in costs]
    n = len(costs)
    if n > 10:
        raise EvidenceError("official executable market prefix is capped at 10 rows")
    if any(value < 0 for value in costs):
        raise EvidenceError("mirror displacement costs must be nonnegative")
    if n < 2:
        return list(range(n)), 0

    # mask -> (score, moves, permutation_prefix)
    dp: dict[int, tuple[int, int, tuple[int, ...]]] = {0: (0, 0, ())}
    for mask in range(1 << n):
        state = dp.get(mask)
        if state is None:
            continue
        score, moves, prefix = state
        position = len(prefix)
        for original in range(n):
            bit = 1 << original
            if mask & bit:
                continue
            candidate = (
                score + _edge_contribution(costs[original], original, position),
                moves + (position != original),
                prefix + (original,),
            )
            next_mask = mask | bit
            incumbent = dp.get(next_mask)
            if incumbent is None:
                dp[next_mask] = candidate
                continue
            # Higher score; then fewer moved rows; then lexicographically stable.
            if (candidate[0], -candidate[1], tuple(-x for x in candidate[2])) > (
                incumbent[0], -incumbent[1], tuple(-x for x in incumbent[2])
            ):
                dp[next_mask] = candidate
    score, _moves, permutation = dp[(1 << n) - 1]
    if score <= 0:
        return list(range(n)), 0
    return list(permutation), score


def competitive_costs(
    model: Any,
    rows: Any,
    market_inventory: Any,
    shed: Any,
    *,
    max_orders: int = 10,
    params=None,
) -> tuple[int, list[dict[str, Any]]]:
    limit, block = _leading_unique_sell_block(
        rows, market_inventory, shed, max_orders=max_orders
    )
    for entry in block:
        entry["exact_mirror_displacement"] = mirror_displacement_cost(
            model, entry["item"], entry["inventory"], entry["fill"], params
        )
        entry["endpoint_proxy"] = endpoint_proxy_cost(
            model, entry["item"], entry["inventory"], entry["fill"], params
        )
    return limit, block


def optimize_mirror_queue(
    model: Any,
    rows: Any,
    market_inventory: Any,
    shed: Any,
    *,
    max_orders: int = 10,
    params=None,
) -> tuple[list[Any], dict[str, Any]]:
    """Return a research-only exact mirror-optimal permutation + certificate."""
    if not isinstance(rows, list):
        raise EvidenceError("market rows must be a list")
    limit, block = competitive_costs(
        model,
        rows,
        market_inventory,
        shed,
        max_orders=max_orders,
        params=params,
    )
    if len(block) < 2:
        return deepcopy(rows), {
            "status": "identity",
            "reason": "leading_unique_sell_block_lt_2",
            "predicted_mirror_edge": 0,
            "entries": block,
        }
    costs = [entry["exact_mirror_displacement"] for entry in block]
    permutation, edge = optimal_indices(costs)
    result = deepcopy(rows)
    result[: len(block)] = [deepcopy(block[i]["row"]) for i in permutation]
    return result, {
        "status": "proposal" if permutation != list(range(len(block))) else "identity",
        "reason": "exact_mirror_assignment",
        "executable_limit": limit,
        "block_len": len(block),
        "permutation": permutation,
        "predicted_mirror_edge": edge,
        "entries": block,
        "non_authority": (
            "research-only; requires separate evidence that the rival current queue mirrors "
            "the incumbent block; no rival current-action observation is assumed"
        ),
    }


def simulate_sell_queues(
    model: Any,
    candidate_rows: Sequence[Sequence[Any]],
    opponent_rows: Sequence[Sequence[Any]],
    market_inventory: dict[str, int],
    shed: dict[str, int],
    *,
    params=None,
) -> tuple[int, int, dict[str, int]]:
    """Direct official-lockstep SELL-only simulator for theorem validation."""
    inventories = {item: _plain_int(level, f"inventory {item}")
                   for item, level in market_inventory.items()}
    stocks = [
        {item: _plain_int(value, f"shed {item}", minimum=0) for item, value in shed.items()},
        {item: _plain_int(value, f"shed {item}", minimum=0) for item, value in shed.items()},
    ]
    queues = [list(candidate_rows), list(opponent_rows)]
    revenue = [0, 0]
    max_len = max(len(queues[0]), len(queues[1]))
    for index in range(max_len):
        states: list[dict[str, Any] | None] = []
        for queue in queues:
            if index >= len(queue):
                states.append(None)
                continue
            row = queue[index]
            if not isinstance(row, (list, tuple)) or len(row) < 3 or row[0] != "SELL":
                raise EvidenceError("simulator accepts SELL-only rows")
            item = row[1]
            qty = _plain_int(row[2], "SELL quantity", minimum=1)
            if not isinstance(item, str) or item not in inventories or item not in shed:
                raise EvidenceError("SELL item missing public/private inventory")
            states.append({"item": item, "remaining": qty})

        while True:
            quoted: list[tuple[str, int] | None] = [None, None]
            for player in (0, 1):
                state = states[player]
                if state is None or state["remaining"] <= 0:
                    continue
                item = state["item"]
                if stocks[player].get(item, 0) <= 0:
                    states[player] = None
                    continue
                price = model.market_price(item, inventories[item], params)
                if type(price) is not int or price < 1:
                    raise EvidenceError("market price must be positive int")
                quoted[player] = (item, price)
            if quoted == [None, None]:
                break
            committed = False
            # Quote both first, then commit in player order, matching official engine.
            for player in (0, 1):
                quote = quoted[player]
                if quote is None:
                    continue
                item, price = quote
                stocks[player][item] -= 1
                revenue[player] += price
                if price > 1:
                    inventories[item] += 1
                assert states[player] is not None
                states[player]["remaining"] -= 1
                committed = True
            if not committed:
                break
    return revenue[0], revenue[1], inventories


def predicted_edge_for_rows(
    model: Any,
    baseline_rows: Sequence[Sequence[Any]],
    candidate_rows: Sequence[Sequence[Any]],
    market_inventory: dict[str, int],
    shed: dict[str, int],
    *,
    params=None,
) -> int:
    """Closed-form mirror edge for unique-product equal-quantity permutations."""
    if len(baseline_rows) != len(candidate_rows):
        raise EvidenceError("candidate must be a permutation of baseline rows")
    base_items = [row[1] for row in baseline_rows]
    cand_items = [row[1] for row in candidate_rows]
    if len(set(base_items)) != len(base_items) or sorted(base_items) != sorted(cand_items):
        raise EvidenceError("rows must be a unique-product permutation")
    candidate_pos = {item: i for i, item in enumerate(cand_items)}
    total = 0
    for original, row in enumerate(baseline_rows):
        if len(row) < 3 or row[0] != "SELL":
            raise EvidenceError("baseline must be SELL-only")
        item = row[1]
        qty = _plain_int(row[2], "SELL quantity", minimum=1)
        fill = min(qty, _plain_int(shed[item], f"shed {item}", minimum=0))
        cost = mirror_displacement_cost(
            model, item, _plain_int(market_inventory[item], f"inventory {item}"), fill, params
        )
        total += _edge_contribution(cost, original, candidate_pos[item])
    return total


def witness(model: Any) -> dict[str, Any]:
    inventory = {"MELON": 10025, "WOOL": 10025}
    shed = {"MELON": 60, "WOOL": 30}
    baseline = [["SELL", "WOOL", 30], ["SELL", "MELON", 60]]
    proposed, cert = optimize_mirror_queue(model, baseline, inventory, shed)
    cand, opp, _ = simulate_sell_queues(model, proposed, baseline, inventory, shed)
    baseline_cand, baseline_opp, _ = simulate_sell_queues(
        model, baseline, baseline, inventory, shed
    )
    return {
        "inventory": inventory,
        "shed": shed,
        "baseline": baseline,
        "proposal": proposed,
        "predicted_edge": cert["predicted_mirror_edge"],
        "direct_candidate_revenue": cand,
        "direct_opponent_revenue": opp,
        "direct_edge": cand - opp,
        "baseline_edge": baseline_cand - baseline_opp,
        "scores": [
            {
                "item": entry["item"],
                "fill": entry["fill"],
                "endpoint_proxy": entry["endpoint_proxy"],
                "exact_mirror_displacement": entry["exact_mirror_displacement"],
            }
            for entry in cert["entries"]
        ],
    }


def scan_proxy_inversions(model: Any) -> dict[str, Any]:
    """Bounded deterministic scan showing proxy/exact ranking disagreement."""
    offsets = (0, 25, 50, 100, 250, 500)
    quantities = (2, 4, 8, 10, 20, 30, 40, 50, 60, 75)
    products = tuple(model.MARKET_PARAMS)
    cache: dict[tuple[str, int, int], tuple[int, int]] = {}
    inversions = 0
    checked = 0
    worst: dict[str, Any] | None = None
    for offset in offsets:
        level = 10000 + offset
        for qa in quantities:
            for qb in quantities:
                if qa + qb > 100:
                    continue
                for a, b in itertools.combinations(products, 2):
                    checked += 1
                    for item, qty in ((a, qa), (b, qb)):
                        key = (item, level, qty)
                        if key not in cache:
                            cache[key] = (
                                endpoint_proxy_cost(model, item, level, qty),
                                mirror_displacement_cost(model, item, level, qty),
                            )
                    pa, ea = cache[(a, level, qa)]
                    pb, eb = cache[(b, level, qb)]
                    if (pa > pb and ea < eb) or (pa < pb and ea > eb):
                        inversions += 1
                        missed = abs(ea - eb)
                        row = {
                            "inventory": level,
                            "a": {"item": a, "qty": qa, "proxy": pa, "exact": ea},
                            "b": {"item": b, "qty": qb, "proxy": pb, "exact": eb},
                            "missed_pair_edge": missed,
                        }
                        if worst is None or missed > worst["missed_pair_edge"]:
                            worst = row
    return {
        "checked_pair_cases": checked,
        "proxy_exact_rank_inversions": inversions,
        "worst_in_grid": worst,
        "inventory_offsets": list(offsets),
        "quantities": list(quantities),
        "shed_feasibility_rule": "qa+qb<=100",
    }


def make_report(model: Any) -> dict[str, Any]:
    return {
        "schema": "titan-v4-sell-queue-competition/v1",
        "mechanics_git_blob": MECHANICS_GIT_BLOB,
        "scope": "research-only mirror SELL-queue competition; no runtime authority",
        "witness": witness(model),
        "proxy_scan": scan_proxy_inversions(model),
        "optimizer": {
            "algorithm": "exact bitmask assignment O(n*2^n)",
            "max_rows": 10,
            "objective": (
                "sum +exact displacement for each row moved earlier than its mirror baseline "
                "position, -exact displacement for each row moved later"
            ),
        },
        "nonclaims": [
            "no rival current-action observability",
            "no proof every hosted opponent mirrors TITAN",
            "no controller/default/config activation",
            "no claim that endpoint proxy is always harmful outside mirror competition",
        ],
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mechanics", type=Path, default=MECHANICS_PATH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        model = load_pinned_mechanics(args.mechanics)
        report = make_report(model)
        payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.output:
            args.output.write_text(payload, encoding="utf-8")
        else:
            print(payload, end="")
        return 0
    except (EvidenceError, OSError, SyntaxError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
