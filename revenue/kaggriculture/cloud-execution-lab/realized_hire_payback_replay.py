# SPDX-License-Identifier: Apache-2.0
"""Official unit/decay replay helpers for the stranded-HIRE certificate."""
from __future__ import annotations
from typing import Any, Mapping, Sequence
import mechanics as m
from realized_hire_payback_common import (
    _ALLOWED_NEW_HAND_OPS, _ONE_TOKEN_OPS, _Reject, _digest,
)

def _market_rows(row: Mapping[str, Any], limit: int) -> list[Any]:
    queue = row.get("market", [])
    if not isinstance(queue, list):
        raise _Reject("unsupported_market_queue")
    if len(queue) > limit:
        raise _Reject("over_limit_market_queue")
    return queue

def _consume_sell_queue(
    private: dict,
    queue: Sequence[Any],
    *,
    allow_hire_index: int | None = None,
) -> dict[str, int]:
    sold = {product: 0 for product in m.PRODUCTS}
    shed = private["shed"]
    for index, row in enumerate(queue):
        if row == []:
            continue
        if allow_hire_index is not None and index == allow_hire_index and row == ["HIRE"]:
            continue
        if not (
            isinstance(row, list)
            and len(row) == 3
            and row[0] == "SELL"
            and isinstance(row[1], str)
            and row[1] in sold
            and isinstance(row[2], int)
            and not isinstance(row[2], bool)
            and row[2] >= 0
        ):
            raise _Reject("unsupported_market_dependency", f"index={index}; row={row!r}"[:240])
        product = row[1]
        completed = min(row[2], shed.get(product, 0))
        if completed:
            shed[product] -= completed
            sold[product] += completed
    return sold

def _route_row(route: Sequence[Any], step: int, limit: int) -> tuple[Mapping[str, Any], list[Any], list[Any]]:
    if step < 0 or step >= len(route):
        raise _Reject("route_step_missing", f"step={step}")
    row = route[step]
    if not isinstance(row, Mapping):
        raise _Reject("unsupported_route_row", f"step={step}")
    hands = row.get("hands", [])
    if not isinstance(hands, list):
        raise _Reject("unsupported_route_hands", f"step={step}")
    if len(hands) > 128:
        raise _Reject("route_hands_unbounded", f"step={step}")
    return row, hands, _market_rows(row, limit)

def _action_op(action: Any) -> str:
    if action == []:
        return "PASS"
    if not isinstance(action, list) or not action or not isinstance(action[0], str):
        raise _Reject("malformed_new_hand_action", repr(action)[:200])
    op = action[0]
    if op not in _ALLOWED_NEW_HAND_OPS:
        raise _Reject("unsupported_new_hand_action", op)
    if op in _ONE_TOKEN_OPS and len(action) != 1:
        raise _Reject("malformed_new_hand_action", repr(action)[:200])
    return op

def _unit_actions(row: Mapping[str, Any], hands: list[Any]) -> list[Any]:
    farmer = row.get("farmer", ["PASS"])
    return [farmer, *hands]

def _blocked_plants(actions: Sequence[Any], private: Mapping[str, Any]) -> set[str]:
    demand: dict[str, int] = {}
    for action in actions:
        if isinstance(action, list) and len(action) >= 2 and action[0] == "PLANT":
            crop = action[1]
            if isinstance(crop, str):
                demand[crop] = demand.get(crop, 0) + 1
    seeds = private.get("seeds", {})
    if not isinstance(seeds, Mapping):
        raise _Reject("invalid_seed_state")
    blocked = set()
    for crop, count in demand.items():
        available = seeds.get(crop, 0)
        if isinstance(available, bool) or not isinstance(available, int) or available < 0:
            raise _Reject("invalid_seed_state", crop)
        if count > available:
            blocked.add(crop)
    return blocked

def _allowed_action(action: Any, blocked: set[str]) -> Any:
    if (
        isinstance(action, list)
        and len(action) >= 2
        and action[0] == "PLANT"
        and action[1] in blocked
    ):
        return ["PASS"]
    return action

def _apply_control_stage(
    farm: dict,
    private: dict,
    actions: Sequence[Any],
    *,
    board_size: int,
    day: int,
    turns_per_day: int,
    shed_capacity: int,
) -> None:
    blocked = _blocked_plants(actions, private)
    for actor_index, action in enumerate(actions):
        m._apply_unit_action(
            farm,
            private,
            actor_index,
            _allowed_action(action, blocked),
            board_size,
            day,
            turns_per_day,
            shed_capacity,
        )

def _apply_candidate_stage(
    farm: dict,
    private: dict,
    actions: Sequence[Any],
    *,
    new_actor_index: int,
    board_size: int,
    day: int,
    turns_per_day: int,
    shed_capacity: int,
) -> tuple[str, str]:
    blocked = _blocked_plants(actions, private)
    before = after = ""
    for actor_index, action in enumerate(actions):
        if actor_index == new_actor_index:
            before = _digest({"farm": farm, "private": private})
        m._apply_unit_action(
            farm,
            private,
            actor_index,
            _allowed_action(action, blocked),
            board_size,
            day,
            turns_per_day,
            shed_capacity,
        )
        if actor_index == new_actor_index:
            after = _digest({"farm": farm, "private": private})
    if not before:
        # Route omitted the new slot.  The official interpreter therefore never
        # called this actor; represent the no-op explicitly.
        before = after = _digest({"farm": farm, "private": private})
    return before, after

def _empty_sales() -> dict[str, int]:
    return {product: 0 for product in m.PRODUCTS}

def _add_sales(total: dict[str, int], increment: Mapping[str, int]) -> None:
    for product in total:
        total[product] += int(increment.get(product, 0))
