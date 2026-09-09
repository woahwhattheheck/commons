#!/usr/bin/env python3
"""Conservative day-reset composition: turn dominated last-tick motion into crop harvest.

The official engine executes unit actions, then market, then end-of-day refresh.  At
hour ``turnsPerDay - 1`` every worker position is reset and every carried item is
auto-deposited up to shed capacity.  Therefore a PASS, or a MOVE whose only effect
is position, may be replaced by HARVEST at the worker's current crop tile when:

* the crop has visible held yield;
* no other co-located worker performs a stateful unit action;
* no second replacement targets that tile; and
* all currently owned physical stock, every selected source action, every possible
  current market purchase, and the proposed harvest fit in the shed together.

The intentionally pessimistic capacity bound ignores current SELL/CONSUME/PLACE
relief.  It can decline useful cases, but it cannot certify storage from a fill that
only exists after assuming a sale or a destructive transition.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping, Sequence


DEFAULT_TURNS_PER_DAY = 24
DEFAULT_SHED_CAPACITY = 100
RESET_DOMINATED_OPS = frozenset(("PASS", "MOVE"))


class Decline(ValueError):
    """Internal fail-closed signal; public callers receive an unchanged action."""


def _int(value: Any, *, minimum: int | None = None, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise Decline(f"{label}-not-integer")
    if minimum is not None and value < minimum:
        raise Decline(f"{label}-below-{minimum}")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise Decline(f"{label}-not-mapping")
    return value


def _sequence(value: Any, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise Decline(f"{label}-not-sequence")
    return value


def _counts_total(value: Any, label: str) -> int:
    rows = _mapping(value, label)
    total = 0
    for item, quantity in rows.items():
        if not isinstance(item, str) or not item:
            raise Decline(f"{label}-bad-item")
        total += _int(quantity, minimum=0, label=f"{label}-{item}-quantity")
    return total


def _position(value: Any, label: str) -> tuple[int, int]:
    row = _sequence(value, label)
    if len(row) != 2:
        raise Decline(f"{label}-wrong-length")
    return (
        _int(row[0], minimum=0, label=f"{label}-x"),
        _int(row[1], minimum=0, label=f"{label}-y"),
    )


def _op(value: Any) -> str:
    if not isinstance(value, list) or not value or not isinstance(value[0], str):
        return "MALFORMED"
    return value[0]


def _tile(grid: Any, position: tuple[int, int]) -> Mapping[str, Any] | None:
    rows = _sequence(grid, "tiles")
    x, y = position
    if y >= len(rows):
        raise Decline("position-y-out-of-range")
    row = _sequence(rows[y], "tile-row")
    if x >= len(row):
        raise Decline("position-x-out-of-range")
    value = row[x]
    if value is None or value == "LOCKED":
        return None
    if not isinstance(value, Mapping):
        raise Decline("tile-not-mapping")
    return value


def _configuration_int(
    configuration: Any,
    key: str,
    default: int,
    *,
    minimum: int,
) -> int:
    if configuration is None:
        return default
    cfg = _mapping(configuration, "configuration")
    return _int(cfg.get(key, default), minimum=minimum, label=key)


def _action_rows(action: Mapping[str, Any], worker_count: int) -> list[list[Any]]:
    farmer = action.get("farmer", ["PASS"])
    if not isinstance(farmer, list):
        raise Decline("farmer-action-not-list")
    hands = action.get("hands", [])
    if not isinstance(hands, list):
        raise Decline("hands-actions-not-list")
    if len(hands) > worker_count - 1:
        raise Decline("too-many-hand-actions")
    rows: list[list[Any]] = [copy.deepcopy(farmer)]
    for row in hands:
        if not isinstance(row, list):
            raise Decline("hand-action-not-list")
        rows.append(copy.deepcopy(row))
    rows.extend([["PASS"]] * (worker_count - len(rows)))
    return rows


def _set_rows(action: Mapping[str, Any], rows: Sequence[list[Any]]) -> dict[str, Any]:
    output = copy.deepcopy(dict(action))
    output["farmer"] = copy.deepcopy(rows[0])
    output["hands"] = copy.deepcopy(list(rows[1:]))
    return output


def _visible_yield(tile: Mapping[str, Any], label: str) -> int:
    return _int(tile.get("yield_units", 0), minimum=0, label=f"{label}-yield")


def _selected_generation_upper(
    rows: Sequence[list[Any]],
    positions: Sequence[tuple[int, int]],
    grid: Any,
) -> int:
    generated = 0
    for worker, row in enumerate(rows):
        operation = _op(row)
        if operation not in ("HARVEST", "COLLECT_FERTILIZER"):
            continue
        tile = _tile(grid, positions[worker])
        if tile is None:
            continue
        if operation == "HARVEST":
            if tile.get("kind") == "PLANT" or "animal" in tile:
                generated += _visible_yield(tile, f"worker-{worker}")
        elif (
            "animal" in tile
            and tile.get("fertilizer_available") is True
        ):
            generated += 1
    return generated


def _market_buy_upper(market: Any) -> int:
    orders = _sequence(market, "market")
    total = 0
    for index, order in enumerate(orders):
        row = _sequence(order, f"market-{index}")
        if not row or not isinstance(row[0], str):
            raise Decline(f"market-{index}-bad-op")
        operation = row[0]
        if operation == "BUY_PRODUCT":
            if len(row) != 3 or not isinstance(row[1], str) or not row[1]:
                raise Decline(f"market-{index}-malformed-buy-product")
            total += _int(row[2], minimum=0, label=f"market-{index}-quantity")
        elif operation == "BUY_ANIMAL":
            if len(row) != 2 or not isinstance(row[1], str) or not row[1]:
                raise Decline(f"market-{index}-malformed-buy-animal")
            total += 1
        elif operation in (
            "SELL",
            "BUY_SEED",
            "HIRE",
            "BUY_LAND",
        ):
            continue
        else:
            # Unknown market rows can create stock under a newer engine.  Do not
            # compose across an operation whose physical effect is not modeled.
            raise Decline(f"market-{index}-unsupported-op")
    return total


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def rewrite_last_tick_crop_harvest(
    observation: Any,
    action: Any,
    configuration: Any = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return ``(action, receipt)`` without mutating either input.

    Any malformed or unmodeled input declines to the original action.  The receipt
    is evaluator telemetry only; callers must not pass it to the game engine as an
    action field unless their harness removes it first.
    """

    original = copy.deepcopy(action) if isinstance(action, dict) else action
    try:
        obs = _mapping(observation, "observation")
        current = _mapping(action, "action")
        turns_per_day = _configuration_int(
            configuration,
            "turnsPerDay",
            DEFAULT_TURNS_PER_DAY,
            minimum=1,
        )
        shed_capacity = _configuration_int(
            configuration,
            "shedCapacity",
            DEFAULT_SHED_CAPACITY,
            minimum=0,
        )
        hour_value = obs.get("hour")
        if hour_value is None:
            step = _int(obs.get("step"), minimum=0, label="step")
            hour = step % turns_per_day
        else:
            hour = _int(hour_value, minimum=0, label="hour")
        if hour != turns_per_day - 1:
            raise Decline("not-last-tick")

        farms = _sequence(obs.get("farms"), "farms")
        player = _int(obs.get("player"), minimum=0, label="player")
        if player >= len(farms):
            raise Decline("player-out-of-range")
        farm = _mapping(farms[player], "farm")
        hands = _sequence(farm.get("hands", []), "hands")
        worker_count = 1 + len(hands)
        positions = [_position(farm.get("farmer"), "farmer-position")]
        positions.extend(
            _position(value, f"hand-{index}-position")
            for index, value in enumerate(hands, 1)
        )
        if len(positions) != worker_count:
            raise Decline("worker-position-count")

        private = _mapping(obs.get("private"), "private")
        inventories = _sequence(private.get("inventories"), "inventories")
        if len(inventories) != worker_count:
            raise Decline("inventory-worker-count")
        physical_total = _counts_total(private.get("shed"), "shed")
        physical_total += sum(
            _counts_total(value, f"inventory-{index}")
            for index, value in enumerate(inventories)
        )

        rows = _action_rows(current, worker_count)
        grid = farm.get("tiles")
        generated_upper = _selected_generation_upper(rows, positions, grid)
        buys_upper = _market_buy_upper(current.get("market", []))
        worst_case_total = physical_total + generated_upper + buys_upper

        groups: dict[tuple[int, int], list[int]] = {}
        for worker, position in enumerate(positions):
            groups.setdefault(position, []).append(worker)

        output_rows = copy.deepcopy(rows)
        used_tiles: set[tuple[int, int]] = set()
        activations: list[dict[str, Any]] = []
        for worker, selected in enumerate(rows):
            selected_operation = _op(selected)
            if selected_operation not in RESET_DOMINATED_OPS:
                continue
            position = positions[worker]
            if position in used_tiles:
                continue
            peers = groups[position]
            if any(
                peer != worker and _op(rows[peer]) not in RESET_DOMINATED_OPS
                for peer in peers
            ):
                continue
            tile = _tile(grid, position)
            if tile is None or tile.get("kind") != "PLANT":
                continue
            crop = tile.get("crop")
            if not isinstance(crop, str) or not crop:
                raise Decline("crop-not-string")
            held = _visible_yield(tile, f"worker-{worker}")
            if held <= 0:
                continue
            if worst_case_total + held > shed_capacity:
                continue
            output_rows[worker] = ["HARVEST"]
            used_tiles.add(position)
            worst_case_total += held
            activations.append(
                {
                    "worker": worker,
                    "position": list(position),
                    "selected_action": copy.deepcopy(selected),
                    "replacement_action": ["HARVEST"],
                    "crop": crop,
                    "visible_yield": held,
                    "worst_case_total_after": worst_case_total,
                    "shed_capacity": shed_capacity,
                }
            )

        rewritten = _set_rows(current, output_rows) if activations else copy.deepcopy(dict(current))
        return rewritten, {
            "schema_version": 1,
            "applied": bool(activations),
            "reason": "last-tick-crop-harvest" if activations else "no-safe-candidate",
            "activations": activations,
            "physical_total_before": physical_total,
            "selected_generation_upper": generated_upper,
            "market_buy_upper": buys_upper,
            "worst_case_total_after": worst_case_total,
            "input_action_sha256": _digest(current),
            "output_action_sha256": _digest(rewritten),
        }
    except (Decline, TypeError, ValueError, OverflowError) as exc:
        unchanged = copy.deepcopy(original) if isinstance(original, dict) else {"farmer": ["PASS"], "hands": [], "market": []}
        return unchanged, {
            "schema_version": 1,
            "applied": False,
            "reason": f"decline:{exc}",
            "activations": [],
            "input_action_sha256": _digest(unchanged),
            "output_action_sha256": _digest(unchanged),
        }


__all__ = ["rewrite_last_tick_crop_harvest"]
