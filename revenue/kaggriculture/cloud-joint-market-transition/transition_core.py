# SPDX-License-Identifier: Apache-2.0
"""Internal support for the exact TITAN joint transition oracle."""
from __future__ import annotations

import time
from typing import Any, Mapping, Sequence

from engine_binding import BudgetExceeded, Struct, _copy, canonical_sha256
from state_contracts import _active_queue


def _numeric_map_delta(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in sorted(set(before) | set(after)):
        b = before.get(key, 0)
        a = after.get(key, 0)
        if isinstance(b, bool) or isinstance(a, bool):
            if a != b:
                result[key] = {"before": b, "after": a}
        elif isinstance(b, (int, float)) and isinstance(a, (int, float)):
            if a != b:
                result[key] = a - b
        elif a != b:
            result[key] = {"before": _copy(b), "after": _copy(a)}
    return result


def _party_effect(before: Mapping[str, Any], after: Mapping[str, Any], player: int) -> dict[str, Any]:
    before_farm = before["farms"][player]
    after_farm = after["farms"][player]
    before_private = before["privates"][player]
    after_private = after["privates"][player]
    return {
        "cash_delta": after_farm["money"] - before_farm["money"],
        "shed_delta": _numeric_map_delta(before_private["shed"], after_private["shed"]),
        "seed_delta": _numeric_map_delta(before_private["seeds"], after_private["seeds"]),
        "hires_today_delta": after_farm["hires_today"] - before_farm["hires_today"],
        "hands_added": _copy(after_farm["hands"][len(before_farm["hands"]):]),
        "land_added": _copy(after_farm["unlocked_quadrants"][len(before_farm["unlocked_quadrants"]):]),
        "inventories_before": _copy(before_private["inventories"]),
        "inventories_after": _copy(after_private["inventories"]),
    }


def _market_effect(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "inventory_delta": _numeric_map_delta(before["market"]["inventory"], after["market"]["inventory"]),
        "price_delta": _numeric_map_delta(before["market"]["prices"], after["market"]["prices"]),
    }


def _execution(mechanics: Any, order: Any, before: Mapping[str, Any], after: Mapping[str, Any], player: int) -> dict[str, Any]:
    parsed = mechanics._parse_order(_copy(order))
    effect = _party_effect(before, after, player)
    result: dict[str, Any] = {
        "raw_order": _copy(order),
        "parsed": _copy(parsed),
        "executed_units": 0,
        "cash_delta": effect["cash_delta"],
        "effect": effect,
    }
    if not parsed:
        return result
    op = parsed["type"]
    item = parsed.get("item")
    if op == "SELL":
        result["executed_units"] = max(
            0,
            before["privates"][player]["shed"].get(item, 0)
            - after["privates"][player]["shed"].get(item, 0),
        )
    elif op in ("BUY_PRODUCT", "BUY_ANIMAL"):
        result["executed_units"] = max(
            0,
            after["privates"][player]["shed"].get(item, 0)
            - before["privates"][player]["shed"].get(item, 0),
        )
    elif op == "BUY_SEED":
        result["executed_units"] = max(
            0,
            after["privates"][player]["seeds"].get(item, 0)
            - before["privates"][player]["seeds"].get(item, 0),
        )
    elif op == "HIRE":
        result["executed_units"] = max(0, len(after["farms"][player]["hands"]) - len(before["farms"][player]["hands"]))
    elif op == "BUY_LAND":
        result["executed_units"] = max(
            0,
            len(after["farms"][player]["unlocked_quadrants"])
            - len(before["farms"][player]["unlocked_quadrants"]),
        )
    return result


def _state_from_inputs(
    farms: Sequence[Mapping[str, Any]],
    privates: Sequence[Mapping[str, Any]],
    market: Mapping[str, Any],
    town: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "farms": _copy(list(farms)),
        "privates": _copy(list(privates)),
        "market": _copy(dict(market)),
        "town": _copy(dict(town)),
    }


def _engine_state(state_value: Mapping[str, Any], actions: Sequence[Mapping[str, Any]]) -> tuple[list[Struct], Struct]:
    farms = state_value["farms"]
    privates = state_value["privates"]
    market = state_value["market"]
    town = state_value["town"]
    states = [
        Struct(
            observation=Struct(farms=farms, private=privates[player], market=market, town=town),
            action=_copy(actions[player]),
        )
        for player in (0, 1)
    ]
    return states, Struct(configuration=Struct())


def _simulate_prefix(
    mechanics: Any,
    prestate: Mapping[str, Any],
    actions: Sequence[Mapping[str, Any]],
    configuration: Mapping[str, Any],
    *,
    step: int,
    prefix_length: int,
    apply_town: bool,
) -> dict[str, Any]:
    state_value = _copy(prestate)
    active_actions = []
    for action in actions:
        next_action = _copy(dict(action))
        next_action["market"] = _copy(action.get("market", [])[:prefix_length])
        active_actions.append(next_action)
    states, env = _engine_state(state_value, active_actions)
    env.configuration.update(_copy(dict(configuration)))
    mechanics._process_market(states, env)
    if apply_town:
        mechanics._town_consume(env, states, step)
    return state_value


def _check_deadline(deadline: float | None) -> None:
    if deadline is not None and time.monotonic() >= deadline:
        raise BudgetExceeded("deadline")


def _work_bound(
    mechanics: Any, actions: Sequence[Mapping[str, Any]],
    farms: Sequence[Mapping[str, Any]], configuration: Mapping[str, int],
    max_orders: int,
) -> int:
    """Conservative deterministic work bound for cumulative prefix replay."""

    queues = [_active_queue(action, max_orders) for action in actions]
    prefix_count = max((len(queue) for queue in queues), default=0)
    work = 0
    for player, queue in enumerate(queues):
        prior_hires = 0
        for index, order in enumerate(queue):
            parsed = mechanics._parse_order(_copy(order))
            repeats = prefix_count - index + 1  # later prefixes plus post-town run
            units = 1
            if parsed and "remaining" in parsed:
                remaining = parsed["remaining"]
                if type(remaining) is not int or remaining < 0:
                    raise ValueError("invalid_parsed_remaining")
                if remaining >= 99_999:
                    raise BudgetExceeded("official_market_iteration_guard")
                units += remaining
            work += units * repeats
            if parsed and parsed["type"] == "HIRE":
                # _fib is linear in hires_today; _spawn_hand scans all workers.
                hire_index = farms[player]["hires_today"] + prior_hires
                worker_count = 1 + len(farms[player]["hands"]) + prior_hires
                work += (hire_index + worker_count + 2) * repeats
                prior_hires += 1
            elif parsed and parsed["type"] == "BUY_LAND":
                work += configuration["boardSize"] ** 2 * repeats
    return work


def _run_arm(
    mechanics: Any,
    prestate: Mapping[str, Any],
    actions: Sequence[Mapping[str, Any]],
    configuration: Mapping[str, Any],
    *,
    step: int,
    deadline: float | None,
) -> dict[str, Any]:
    max_orders = max(1, configuration["maxMarketOrdersPerTurn"])
    active = [_active_queue(action, max_orders) for action in actions]
    suffix = [_copy(action.get("market", [])[max_orders:]) for action in actions]
    active_length = max((len(queue) for queue in active), default=0)

    initial = _copy(prestate)
    prefixes: list[dict[str, Any]] = [{
        "prefix_length": 0,
        "state_hash": canonical_sha256(initial),
        "state": initial,
        "orders": [None, None],
        "executions": [None, None],
        "market_effect": {"inventory_delta": {}, "price_delta": {}},
    }]
    previous = initial
    for prefix_length in range(1, active_length + 1):
        _check_deadline(deadline)
        current = _simulate_prefix(
            mechanics,
            prestate,
            actions,
            configuration,
            step=step,
            prefix_length=prefix_length,
            apply_town=False,
        )
        orders = [
            _copy(active[player][prefix_length - 1])
            if prefix_length - 1 < len(active[player])
            else None
            for player in (0, 1)
        ]
        prefixes.append({
            "prefix_length": prefix_length,
            "state_hash": canonical_sha256(current),
            "state": current,
            "orders": orders,
            "executions": [
                _execution(mechanics, orders[player], previous, current, player)
                if orders[player] is not None
                else {
                    "raw_order": None,
                    "parsed": None,
                    "executed_units": 0,
                    "cash_delta": current["farms"][player]["money"] - previous["farms"][player]["money"],
                    "effect": _party_effect(previous, current, player),
                }
                for player in (0, 1)
            ],
            "market_effect": _market_effect(previous, current),
        })
        previous = current

    _check_deadline(deadline)
    pre_town = prefixes[-1]["state"]
    post_town = _simulate_prefix(
        mechanics,
        prestate,
        actions,
        configuration,
        step=step,
        prefix_length=active_length,
        apply_town=True,
    )
    return {
        "active_queues": active,
        "ignored_suffixes": suffix,
        "active_action_hash": canonical_sha256(active),
        "ignored_suffix_hash": canonical_sha256(suffix),
        "prefixes": prefixes,
        "pre_town_state": pre_town,
        "pre_town_state_hash": canonical_sha256(pre_town),
        "post_town_state": post_town,
        "post_town_state_hash": canonical_sha256(post_town),
        "town_effect": _market_effect(pre_town, post_town),
    }
