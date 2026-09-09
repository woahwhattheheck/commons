#!/usr/bin/env python3
"""Compose reset-dominated last-tick motion into resource-free crop WATER.

At the final tick of a normal day, the official interpreter applies unit actions,
then resets every worker position during end-of-day refresh.  A PASS or MOVE whose
only effect is that soon-erased position can therefore WATER the worker's current
crop tile instead, provided no co-located stateful action owns that tile.

This helper deliberately does not harvest, sell, consume, fertilize, feed, care,
pathfind, or alter market rows.  It reads only the current public farm state and
returns the original action byte-equivalent on malformed or unmodeled input.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping, Sequence


DEFAULT_TURNS_PER_DAY = 24
RESET_DOMINATED_OPS = frozenset(("PASS", "MOVE"))


class Decline(ValueError):
    """Internal fail-closed signal."""


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


def _action_rows(action: Mapping[str, Any], worker_count: int) -> list[list[Any]]:
    farmer = action.get("farmer", ["PASS"])
    hands = action.get("hands", [])
    if not isinstance(farmer, list):
        raise Decline("farmer-action-not-list")
    if not isinstance(hands, list):
        raise Decline("hands-actions-not-list")
    if len(hands) > worker_count - 1:
        raise Decline("too-many-hand-actions")
    rows = [copy.deepcopy(farmer)]
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


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def rewrite_last_tick_crop_water(
    observation: Any,
    action: Any,
    configuration: Any = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return ``(rewritten_action, receipt)`` without mutating either input."""

    original = copy.deepcopy(action) if isinstance(action, dict) else {
        "farmer": ["PASS"], "hands": [], "market": []
    }
    try:
        obs = _mapping(observation, "observation")
        current = _mapping(action, "action")
        cfg = {} if configuration is None else _mapping(configuration, "configuration")
        turns_per_day = _int(
            cfg.get("turnsPerDay", DEFAULT_TURNS_PER_DAY),
            minimum=1,
            label="turnsPerDay",
        )
        if obs.get("hour") is None:
            step = _int(obs.get("step"), minimum=0, label="step")
            hour = step % turns_per_day
        else:
            hour = _int(obs.get("hour"), minimum=0, label="hour")
        if hour != turns_per_day - 1:
            raise Decline("not-last-tick")

        farms = _sequence(obs.get("farms"), "farms")
        player = _int(obs.get("player"), minimum=0, label="player")
        if player >= len(farms):
            raise Decline("player-out-of-range")
        farm = _mapping(farms[player], "farm")
        hands = _sequence(farm.get("hands", []), "hands")
        positions = [_position(farm.get("farmer"), "farmer-position")]
        positions.extend(
            _position(value, f"hand-{index}-position")
            for index, value in enumerate(hands, 1)
        )
        rows = _action_rows(current, len(positions))
        groups: dict[tuple[int, int], list[int]] = {}
        for worker, position in enumerate(positions):
            groups.setdefault(position, []).append(worker)

        output_rows = copy.deepcopy(rows)
        used_tiles: set[tuple[int, int]] = set()
        activations: list[dict[str, Any]] = []
        for worker, selected in enumerate(rows):
            selected_op = _op(selected)
            if selected_op not in RESET_DOMINATED_OPS:
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
            tile = _tile(farm.get("tiles"), position)
            if tile is None or tile.get("kind") != "PLANT":
                continue
            crop = tile.get("crop")
            if not isinstance(crop, str) or not crop:
                raise Decline("crop-not-string")
            if tile.get("watered_today") is not False:
                continue
            yield_before = _int(
                tile.get("yield_units", 0), minimum=0, label="yield-units"
            )
            consecutive = _int(
                tile.get("consecutive_unwatered", 0),
                minimum=0,
                label="consecutive-unwatered",
            )
            planted_day = _int(
                tile.get("planted_day"), minimum=0, label="planted-day"
            )
            output_rows[worker] = ["WATER"]
            used_tiles.add(position)
            activations.append(
                {
                    "worker": worker,
                    "position": list(position),
                    "selected_action": copy.deepcopy(selected),
                    "replacement_action": ["WATER"],
                    "crop": crop,
                    "visible_yield": yield_before,
                    "yield_before": yield_before,
                    "consecutive_unwatered_before": consecutive,
                    "planted_day": planted_day,
                    "effect_class": (
                        "prevents-immediate-weed"
                        if consecutive >= 1
                        else "resets-water-clock-or-produces"
                    ),
                }
            )

        rewritten = (
            _set_rows(current, output_rows)
            if activations
            else copy.deepcopy(dict(current))
        )
        return rewritten, {
            "schema_version": 1,
            "applied": bool(activations),
            "reason": "last-tick-crop-water" if activations else "no-safe-candidate",
            "activations": activations,
            "input_action_sha256": _digest(current),
            "output_action_sha256": _digest(rewritten),
        }
    except (Decline, TypeError, ValueError, OverflowError) as exc:
        unchanged = copy.deepcopy(original)
        return unchanged, {
            "schema_version": 1,
            "applied": False,
            "reason": f"decline:{exc}",
            "activations": [],
            "input_action_sha256": _digest(unchanged),
            "output_action_sha256": _digest(unchanged),
        }


__all__ = ["rewrite_last_tick_crop_water"]
