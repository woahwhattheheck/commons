# SPDX-License-Identifier: Apache-2.0
"""Fail-closed admission guard for a witnessed seed-prebuy / HIRE regression.

This candidate does not run a producer, predict rival receipts, or mutate a
controller. It compares two already-selected actions for one represented route
step and may choose the predecessor action only when an exact, narrow edit and a
full represented next-day workforce commitment are both proved.

The intended seam is paired V1/V2 candidate evaluation. Promotion still needs
matched-engine evidence outside this module.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping, Sequence

PASS = ("PASS",)
_SUPPORTED_MARKET = {
    "SELL", "BUY_SEED", "HIRE", "BUY_ANIMAL", "BUY_LAND", "BUY_PRODUCT", "PASS"
}


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _orders(action: Mapping[str, Any]) -> list[list[Any]]:
    market = action.get("market", [])
    if not isinstance(market, list):
        raise ValueError("market must be a list")
    result: list[list[Any]] = []
    for index, order in enumerate(market):
        if not isinstance(order, list) or not order or not isinstance(order[0], str):
            raise ValueError(f"market[{index}] must be a nonempty order list")
        if order[0] not in _SUPPORTED_MARKET:
            raise ValueError(f"unsupported market operation {order[0]}")
        result.append(order)
    return result


def _quantity(order: Sequence[Any]) -> int:
    if order[0] in ("HIRE", "BUY_LAND", "PASS"):
        if len(order) != 1:
            raise ValueError(f"{order[0]} order must have one field")
        return 1
    if len(order) != 3:
        raise ValueError("quantity order must have exactly three fields")
    return _integer(order[2], "order quantity")


def action_fingerprint(action: Mapping[str, Any]) -> str:
    raw = json.dumps(action, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(raw.encode("utf-8")).hexdigest()


def _is_pass(action: Any) -> bool:
    return isinstance(action, list) and tuple(action) == PASS


def represented_plant_requests(
    route: Sequence[Mapping[str, Any]], start: int, end: int
) -> dict[str, int]:
    """Count literal represented PLANT requests over an inclusive route range."""
    result: dict[str, int] = {}
    for step in range(max(0, start), min(len(route), end + 1)):
        row = route[step]
        if not isinstance(row, Mapping):
            raise ValueError("route row must be a mapping")
        hands = row.get("hands", [])
        if not isinstance(hands, list):
            raise ValueError("route hands must be a list")
        actors = [row.get("farmer", ["PASS"]), *hands]
        for actor in actors:
            if isinstance(actor, list) and len(actor) > 1 and actor[0] == "PLANT":
                crop = str(actor[1])
                result[crop] = result.get(crop, 0) + 1
    return result


def _exact_edit(predecessor: list[list[Any]], candidate: list[list[Any]]) -> dict[str, Any]:
    """Prove candidate = predecessor + one seed row + one one-unit SELL increase.

    Every other row is byte-equal and retains order. This deliberately rejects
    aggregate-equivalent reorderings or any second market edit.
    """
    if len(candidate) != len(predecessor) + 1:
        raise ValueError("candidate must insert exactly one market row")
    i = j = 0
    inserted: tuple[int, str, int] | None = None
    sale_edit: tuple[int, str, int] | None = None
    while i < len(predecessor) and j < len(candidate):
        before, after = predecessor[i], candidate[j]
        if before == after:
            _quantity(before)
            i += 1
            j += 1
            continue
        if (inserted is None and after[0] == "BUY_SEED" and len(after) == 3):
            crop = str(after[1])
            quantity = _quantity(after)
            if quantity <= 0:
                raise ValueError("inserted seed quantity must be positive")
            inserted = (j, crop, quantity)
            j += 1
            continue
        if (sale_edit is None and before[0] == after[0] == "SELL"
                and len(before) == len(after) == 3 and before[1] == after[1]):
            old = _quantity(before)
            new = _quantity(after)
            if new - old != 1:
                raise ValueError("SELL edit must add exactly one unit")
            sale_edit = (j, str(after[1]), 1)
            i += 1
            j += 1
            continue
        raise ValueError("candidate has an unsupported second market edit")
    if i != len(predecessor):
        raise ValueError("candidate removed a predecessor order")
    if j < len(candidate):
        if j != len(candidate) - 1 or inserted is not None:
            raise ValueError("candidate has extra trailing orders")
        order = candidate[j]
        if order[0] != "BUY_SEED" or len(order) != 3:
            raise ValueError("only one trailing seed insertion is supported")
        quantity = _quantity(order)
        if quantity <= 0:
            raise ValueError("inserted seed quantity must be positive")
        inserted = (j, str(order[1]), quantity)
    if inserted is None or sale_edit is None:
        raise ValueError("candidate must contain one seed insertion and one SELL increment")
    return {
        "seed_insert_index": inserted[0],
        "crop": inserted[1],
        "added_seed_quantity": inserted[2],
        "sell_index": sale_edit[0],
        "sell_item": sale_edit[1],
        "sell_quantity_delta": sale_edit[2],
    }


def find_committed_hire(
    route: Sequence[Mapping[str, Any]],
    now: int,
    configuration: Mapping[str, Any] | None = None,
    *,
    route_switch_steps: Iterable[int] = (),
    max_lookahead: int = 48,
) -> dict[str, Any]:
    """Prove a full next-day HIRE bundle owns a represented actor tape.

    The certified HIRE must occur at the next day boundary. Its represented
    market queue must contain HIRE only, and every subsequent row through the
    following day boundary must expose exactly that many hand slots. Every slot,
    including the trailing one, must receive at least one non-PASS command.
    Unknown, truncated, switched, or irregular shapes fail closed.
    """
    report: dict[str, Any] = {"certified": False, "reason": "invalid_input"}
    try:
        now = _integer(now, "now")
        max_lookahead = _integer(max_lookahead, "max_lookahead", 1)
        if not isinstance(route, Sequence) or now >= len(route):
            raise ValueError("route does not represent the current step")
        config = dict(configuration or {})
        max_orders = _integer(config.get("maxMarketOrdersPerTurn", 10), "market order limit", 1)
        turns = _integer(config.get("turnsPerDay", 24), "turns per day", 1)
        hire_step = (now // turns + 1) * turns
        boundary = hire_step + turns
        hard_end = min(len(route) - 1, now + max_lookahead)
        if boundary > hard_end:
            report["reason"] = "next_day_workforce_window_not_fully_represented"
            return report
        switches = sorted({_integer(step, "route switch step") for step in route_switch_steps if step > now})
        if switches and switches[0] <= boundary:
            report.update(reason="route_switch_crosses_workforce_window", route_switch_step=switches[0])
            return report

        row = route[hire_step]
        if not isinstance(row, Mapping):
            raise ValueError("HIRE route row must be a mapping")
        market = row.get("market", [])
        if not isinstance(market, list) or not market or len(market) > max_orders:
            raise ValueError("HIRE market queue is not fully represented")
        if any(not isinstance(order, list) or order != ["HIRE"] for order in market):
            report["reason"] = "next_day_market_is_not_hire_only"
            return report
        hires = len(market)
        if row.get("hands", []) not in ([], None):
            report["reason"] = "next_day_hire_row_has_preexisting_hand_actions"
            return report

        next_row = route[boundary]
        next_market = next_row.get("market", []) if isinstance(next_row, Mapping) else None
        if not isinstance(next_market, list) or not any(order == ["HIRE"] for order in next_market):
            report["reason"] = "following_day_hire_boundary_missing"
            return report

        demanded_slots = [False] * hires
        productive_trailing_rows = 0
        for future in range(hire_step + 1, boundary):
            future_row = route[future]
            if not isinstance(future_row, Mapping):
                raise ValueError("workforce route row must be a mapping")
            hands = future_row.get("hands", [])
            if not isinstance(hands, list) or len(hands) != hires:
                report.update(reason="workforce_cardinality_is_not_contiguous", failed_step=future)
                return report
            for index, actor in enumerate(hands):
                if not isinstance(actor, list) or not actor:
                    raise ValueError("hand action must be a nonempty list")
                if not _is_pass(actor):
                    demanded_slots[index] = True
            if not _is_pass(hands[-1]):
                productive_trailing_rows += 1
        if not all(demanded_slots) or not productive_trailing_rows:
            report.update(reason="no_contiguous_committed_hire", demanded_slots=demanded_slots)
            return report
        return {
            "certified": True,
            "reason": "full_next_day_workforce_committed",
            "hire_step": hire_step,
            "hire_count": hires,
            "demand_start": hire_step + 1,
            "demand_end": boundary - 1,
            "following_hire_step": boundary,
            "represented_rows": boundary - hire_step - 1,
            "productive_trailing_rows": productive_trailing_rows,
            "demanded_slots": demanded_slots,
        }
    except (IndexError, KeyError, TypeError, ValueError) as error:
        report["reason"] = str(error)
        return report


def protect_committed_hire_seed_boundary(
    predecessor_action: Mapping[str, Any],
    candidate_action: Mapping[str, Any],
    route: Sequence[Mapping[str, Any]],
    now: int,
    configuration: Mapping[str, Any] | None = None,
    *,
    post_unit_seeds: Mapping[str, Any] | None = None,
    route_switch_steps: Iterable[int] = (),
    max_lookahead: int = 48,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Choose the predecessor only for the exact opening all-prefix prebuy hazard.

    This is intentionally stronger than necessary. A false negative preserves
    the candidate; a malformed or ambiguous case never rewrites gameplay.
    """
    report: dict[str, Any] = {
        "changed": False,
        "certified": False,
        "reason": "invalid_input",
        "scope": "one_opening_selected_action",
        "controller_calls": 0,
        "rival_state_used": False,
    }
    try:
        fallback = deepcopy(dict(candidate_action))
    except (TypeError, ValueError):
        return {}, report
    try:
        config = dict(configuration or {})
        maximum = _integer(config.get("maxMarketOrdersPerTurn", 10), "market order limit", 1)
        now = _integer(now, "now")
        if now != 1:
            report["reason"] = "outside_witnessed_opening_step"
            return fallback, report
        if {key: value for key, value in predecessor_action.items() if key != "market"} != {
            key: value for key, value in candidate_action.items() if key != "market"
        }:
            raise ValueError("unit actions differ")
        predecessor = _orders(predecessor_action)
        candidate = _orders(candidate_action)
        if len(predecessor) != maximum - 1 or len(candidate) != maximum:
            raise ValueError("opening queues do not straddle the market-slot boundary")
        edit = _exact_edit(predecessor, candidate)

        witness = find_committed_hire(
            route, now, config, route_switch_steps=route_switch_steps,
            max_lookahead=max_lookahead,
        )
        report["hire_witness"] = witness
        if not witness.get("certified"):
            report["reason"] = witness.get("reason", "no committed HIRE")
            return fallback, report

        crop = edit["crop"]
        plants = represented_plant_requests(route, now + 1, int(witness["hire_step"]) - 1)
        required = int(plants.get(crop, 0))
        stock = dict(post_unit_seeds or {})
        existing = _integer(stock.get(crop, 0), f"{crop} post-unit seed stock")
        predecessor_seed_quantity = sum(
            _quantity(order) for order in predecessor
            if order[0] == "BUY_SEED" and len(order) > 1 and str(order[1]) == crop
        )
        if (existing or predecessor_seed_quantity or required <= 1
                or edit["added_seed_quantity"] != required):
            report.update(
                reason="seed_bundle_is_not_exact_zero_stock_prefix",
                crop=crop,
                added_seed_quantity=edit["added_seed_quantity"],
                prefix_plant_requests=required,
                post_unit_seed_stock=existing,
                predecessor_seed_quantity=predecessor_seed_quantity,
            )
            return fallback, report

        chosen = deepcopy(dict(predecessor_action))
        report.update(
            changed=True,
            certified=True,
            reason="protected_committed_hire_from_all_prefix_seed_prebuy",
            crop=crop,
            added_seed_quantity=edit["added_seed_quantity"],
            prefix_plant_requests=required,
            sell_item=edit["sell_item"],
            sell_quantity_delta=edit["sell_quantity_delta"],
            seed_insert_index=edit["seed_insert_index"],
            predecessor_fingerprint=action_fingerprint(predecessor_action),
            candidate_fingerprint=action_fingerprint(candidate_action),
            chosen_fingerprint=action_fingerprint(chosen),
            preserved_predecessor_exactly=chosen == predecessor_action,
        )
        return chosen, report
    except (IndexError, KeyError, TypeError, ValueError) as error:
        report["reason"] = str(error)
        return fallback, report
