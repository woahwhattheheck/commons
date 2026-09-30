#!/usr/bin/env python3
"""Strict economic-program differential for Kaggriculture episode replays.

This tool is deliberately observational. It separates returned/requested actions
from state transitions and never labels an observed difference as causal proof.
It accepts raw replay JSON, gzip-compressed JSON, and common
EpisodeService/GetEpisodeReplay envelopes.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "titan.kaggriculture.replay-program-diff.v1"
MAX_COMPRESSED_BYTES = 512 * 1024 * 1024
MAX_DECOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024
SEED_COST = {
    "WHEAT": 10,
    "CARROT": 20,
    "TOMATO": 50,
    "STRAWBERRY": 100,
    "MELON": 80,
}
QUANTITY_MARKET_OPS = {"BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"}
MARKET_OPS = QUANTITY_MARKET_OPS | {"HIRE", "BUY_LAND"}
ECONOMIC_UNIT_OPS = {
    "PLANT",
    "HARVEST",
    "FERTILIZE",
    "BUILD_COOP",
    "BUILD_PASTURE",
    "DIG",
    "PLACE",
    "FEED",
    "COLLECT_FERTILIZER",
    "CARE",
    "PICKUP",
}


class ReplayError(ValueError):
    """Raised when an input cannot be admitted as a strict replay."""


def _reject_constant(token: str) -> None:
    raise ReplayError(f"non-finite JSON constant is forbidden: {token}")


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ReplayError(f"duplicate JSON object key: {key!r}")
        out[key] = value
    return out


def _assert_finite(value: Any, path: str = "$") -> None:
    if isinstance(value, bool) or value is None or isinstance(value, (str, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ReplayError(f"non-finite number at {path}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _assert_finite(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _assert_finite(item, f"{path}.{key}")
        return
    raise ReplayError(f"unsupported JSON value at {path}: {type(value).__name__}")


def strict_json_loads(text: str, source: str = "<memory>") -> Any:
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object_without_duplicates,
            parse_constant=_reject_constant,
        )
    except ReplayError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReplayError(f"invalid JSON in {source}: {exc}") from exc
    _assert_finite(value)
    return value


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_input(path: Path) -> tuple[Any, dict[str, Any]]:
    raw = path.read_bytes()
    if len(raw) > MAX_COMPRESSED_BYTES:
        raise ReplayError(
            f"input exceeds compressed-size limit: {len(raw)} > {MAX_COMPRESSED_BYTES}"
        )
    is_gzip = raw.startswith(b"\x1f\x8b")
    decoded = gzip.decompress(raw) if is_gzip else raw
    if len(decoded) > MAX_DECOMPRESSED_BYTES:
        raise ReplayError(
            f"input exceeds decompressed-size limit: {len(decoded)} > {MAX_DECOMPRESSED_BYTES}"
        )
    try:
        text = decoded.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReplayError(f"input is not strict UTF-8: {exc}") from exc
    payload = strict_json_loads(text, str(path))
    return payload, {
        "path": str(path),
        "compressed": is_gzip,
        "input_bytes": len(raw),
        "decoded_bytes": len(decoded),
        "input_sha256": _sha256(raw),
        "decoded_sha256": _sha256(decoded),
    }


def _parse_nested_json(value: Any, label: str) -> Any:
    if isinstance(value, str):
        return strict_json_loads(value, label)
    return value


def unwrap_replay(payload: Any) -> tuple[dict[str, Any], list[str]]:
    """Return a replay object and the envelope path used to reach it."""
    value = payload
    path: list[str] = []
    for _ in range(8):
        value = _parse_nested_json(value, ".".join(path) or "$payload")
        if isinstance(value, dict) and isinstance(value.get("steps"), list):
            return value, path
        if not isinstance(value, dict):
            break

        candidates: list[tuple[str, Any]] = []
        for key in ("replay", "result", "episodeReplay", "episode_replay", "data"):
            if key in value:
                candidates.append((key, value[key]))
        selected: tuple[str, Any] | None = None
        for candidate in candidates:
            nested = candidate[1]
            if isinstance(nested, str) and ("\"steps\"" in nested or "'steps'" in nested):
                selected = candidate
                break
            if isinstance(nested, dict) and (
                "steps" in nested or "replay" in nested or "result" in nested
            ):
                selected = candidate
                break
        if selected is None and len(candidates) == 1:
            selected = candidates[0]
        if selected is None:
            break
        key, value = selected
        path.append(key)
    raise ReplayError("could not locate a replay object with a steps array")


def _as_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ReplayError(f"{label} must be an object")
    return value


def _numeric(value: Any, label: str, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ReplayError(f"{label} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ReplayError(f"{label} must be finite")
    return result


def _integer(value: Any, label: str, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReplayError(f"{label} must be an integer")
    return value


def validate_replay(replay: Mapping[str, Any]) -> tuple[list[list[Mapping[str, Any]]], int]:
    raw_steps = replay.get("steps")
    if not isinstance(raw_steps, list) or len(raw_steps) < 2:
        raise ReplayError("replay.steps must contain at least two state frames")
    if not isinstance(raw_steps[0], list) or len(raw_steps[0]) < 2:
        raise ReplayError("replay must contain at least two players")
    player_count = len(raw_steps[0])
    steps: list[list[Mapping[str, Any]]] = []
    for step_index, raw_step in enumerate(raw_steps):
        if not isinstance(raw_step, list) or len(raw_step) != player_count:
            raise ReplayError(
                f"steps[{step_index}] must contain exactly {player_count} player states"
            )
        step: list[Mapping[str, Any]] = []
        for player, raw_state in enumerate(raw_step):
            state = _as_mapping(raw_state, f"steps[{step_index}][{player}]")
            _as_mapping(
                state.get("observation"),
                f"steps[{step_index}][{player}].observation",
            )
            step.append(state)
        steps.append(step)
    return steps, player_count


def _number_map(value: Any, label: str) -> dict[str, float]:
    if value is None:
        return {}
    mapping = _as_mapping(value, label)
    result: dict[str, float] = {}
    for key, item in mapping.items():
        result[str(key).upper()] = _numeric(item, f"{label}.{key}")
    return result


def _sum_inventories(value: Any, label: str) -> dict[str, float]:
    if value is None:
        return {}
    if not isinstance(value, list):
        raise ReplayError(f"{label} must be an array")
    total: collections.Counter[str] = collections.Counter()
    for index, inventory in enumerate(value):
        for item, quantity in _number_map(inventory, f"{label}[{index}]").items():
            total[item] += quantity
    return dict(sorted(total.items()))


def _tile_summary(value: Any, label: str) -> tuple[dict[str, int], dict[str, float]]:
    if not isinstance(value, list):
        return {}, {}
    counts: collections.Counter[str] = collections.Counter()
    yields: collections.Counter[str] = collections.Counter()
    for y, row in enumerate(value):
        if not isinstance(row, list):
            raise ReplayError(f"{label}[{y}] must be an array")
        for x, cell in enumerate(row):
            if cell is None:
                continue
            if isinstance(cell, str):
                counts[f"TOKEN:{cell.upper()}"] += 1
                continue
            if not isinstance(cell, dict):
                raise ReplayError(f"{label}[{y}][{x}] has unsupported tile value")
            kind = str(cell.get("kind", "UNKNOWN")).upper()
            crop = cell.get("crop")
            animal = cell.get("animal")
            if crop is not None:
                key = f"{kind}:{str(crop).upper()}"
            elif animal is not None:
                key = f"{kind}:{str(animal).upper()}"
            else:
                key = kind
            counts[key] += 1
            yields[key] += _numeric(
                cell.get("yield_units"), f"{label}[{y}][{x}].yield_units", 0.0
            )
    return dict(sorted(counts.items())), dict(sorted(yields.items()))


def _snapshot(observation: Mapping[str, Any], player: int, label: str) -> dict[str, Any]:
    farms = observation.get("farms")
    if not isinstance(farms, list) or player >= len(farms):
        raise ReplayError(f"{label}.farms does not contain player {player}")
    farm = _as_mapping(farms[player], f"{label}.farms[{player}]")
    private = _as_mapping(observation.get("private"), f"{label}.private")
    market = _as_mapping(observation.get("market", {}), f"{label}.market")
    tiles, tile_yields = _tile_summary(farm.get("tiles", []), f"{label}.tiles")
    hands = farm.get("hands", [])
    quadrants = farm.get("unlocked_quadrants", [])
    if not isinstance(hands, list) or not isinstance(quadrants, list):
        raise ReplayError(f"{label} hand/quadrant fields must be arrays")
    return {
        "day": _integer(observation.get("day"), f"{label}.day"),
        "hour": _integer(observation.get("hour"), f"{label}.hour"),
        "cash": _numeric(farm.get("money"), f"{label}.money"),
        "hands": len(hands),
        "quadrants": len(quadrants),
        "hires_today": _integer(farm.get("hires_today"), f"{label}.hires_today"),
        "shed": _number_map(private.get("shed", {}), f"{label}.private.shed"),
        "seeds": _number_map(private.get("seeds", {}), f"{label}.private.seeds"),
        "carried": _sum_inventories(
            private.get("inventories", []), f"{label}.private.inventories"
        ),
        "tiles": tiles,
        "tile_yield_units": tile_yields,
        "market_inventory": _number_map(
            market.get("inventory", {}), f"{label}.market.inventory"
        ),
        "market_prices": _number_map(market.get("prices", {}), f"{label}.market.prices"),
    }


def _mapping_delta(after: Mapping[str, float], before: Mapping[str, float]) -> dict[str, float]:
    keys = set(after) | set(before)
    return {
        key: after.get(key, 0.0) - before.get(key, 0.0)
        for key in sorted(keys)
        if after.get(key, 0.0) != before.get(key, 0.0)
    }


def _integer_mapping_delta(after: Mapping[str, int], before: Mapping[str, int]) -> dict[str, int]:
    keys = set(after) | set(before)
    return {
        key: int(after.get(key, 0)) - int(before.get(key, 0))
        for key in sorted(keys)
        if int(after.get(key, 0)) != int(before.get(key, 0))
    }


def _coerce_action(value: Any, label: str) -> Mapping[str, Any]:
    if value is None:
        return {"farmer": ["PASS"], "hands": [], "market": []}
    if isinstance(value, str):
        value = strict_json_loads(value, label)
    return _as_mapping(value, label)


def _normalize_order(row: Any, label: str) -> tuple[str, list[Any]]:
    if not isinstance(row, list) or not row:
        raise ReplayError(f"{label} must be a non-empty action array")
    if not isinstance(row[0], str) or not row[0].strip():
        raise ReplayError(f"{label}[0] must be a non-empty operation string")
    return row[0].upper(), list(row[1:])


def _event_item_and_quantity(op: str, args: Sequence[Any], label: str) -> tuple[str | None, float]:
    item: str | None = None
    quantity = 1.0
    if op in QUANTITY_MARKET_OPS:
        if len(args) < 2:
            raise ReplayError(f"{label} {op} requires item and quantity")
        item = str(args[0]).upper()
        quantity = _numeric(args[1], f"{label}.quantity")
    elif op in {"PLANT", "PLACE", "PICKUP"}:
        if not args:
            raise ReplayError(f"{label} {op} requires an item")
        item = str(args[0]).upper()
        if len(args) >= 2:
            quantity = _numeric(args[1], f"{label}.quantity")
    return item, quantity


def _action_events(value: Any, label: str) -> list[dict[str, Any]]:
    action = _coerce_action(value, label)
    events: list[dict[str, Any]] = []
    farmer = action.get("farmer", ["PASS"])
    op, args = _normalize_order(farmer, f"{label}.farmer")
    item, quantity = _event_item_and_quantity(op, args, f"{label}.farmer")
    events.append(
        {
            "surface": "farmer",
            "actor_index": 0,
            "op": op,
            "args": args,
            "item": item,
            "quantity": quantity,
        }
    )
    hands = action.get("hands", [])
    if not isinstance(hands, list):
        raise ReplayError(f"{label}.hands must be an array")
    for index, row in enumerate(hands, start=1):
        op, args = _normalize_order(row, f"{label}.hands[{index - 1}]")
        item, quantity = _event_item_and_quantity(op, args, f"{label}.hands[{index - 1}]")
        events.append(
            {
                "surface": "hand",
                "actor_index": index,
                "op": op,
                "args": args,
                "item": item,
                "quantity": quantity,
            }
        )
    market = action.get("market", [])
    if not isinstance(market, list):
        raise ReplayError(f"{label}.market must be an array")
    for index, row in enumerate(market):
        op, args = _normalize_order(row, f"{label}.market[{index}]")
        item, quantity = _event_item_and_quantity(op, args, f"{label}.market[{index}]")
        events.append(
            {
                "surface": "market",
                "actor_index": index,
                "op": op,
                "args": args,
                "item": item,
                "quantity": quantity,
            }
        )
    return events


def _economic_events(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        dict(event)
        for event in events
        if event["op"] in MARKET_OPS or event["op"] in ECONOMIC_UNIT_OPS
    ]


def _event_key(event: Mapping[str, Any]) -> str:
    item = event.get("item")
    return f"{event['op']}:{item}" if item else str(event["op"])


def _liquid_proxy(snapshot: Mapping[str, Any]) -> tuple[float, list[str]]:
    prices = snapshot["market_prices"]
    total = float(snapshot["cash"])
    unresolved: set[str] = set()
    for field in ("shed", "carried"):
        for item, quantity in snapshot[field].items():
            if item in prices:
                total += quantity * prices[item]
            else:
                unresolved.add(item)
    for crop, quantity in snapshot["seeds"].items():
        if crop in SEED_COST:
            total += quantity * SEED_COST[crop]
        else:
            unresolved.add(f"SEED:{crop}")
    return total, sorted(unresolved)


def _shared_digest(observation: Mapping[str, Any]) -> str:
    shared = {
        key: observation.get(key)
        for key in ("farms", "market", "town", "day", "hour")
    }
    return _sha256(_canonical_json_bytes(shared))


def _observation(step: Sequence[Mapping[str, Any]], player: int, step_index: int) -> Mapping[str, Any]:
    return _as_mapping(
        step[player].get("observation"),
        f"steps[{step_index}][{player}].observation",
    )


def _identity_from_replay(replay: Mapping[str, Any]) -> dict[str, Any]:
    info = replay.get("info", {})
    info = info if isinstance(info, dict) else {}
    candidates = {
        "episode_id": (
            replay.get("id")
            or replay.get("episodeId")
            or replay.get("episode_id")
            or info.get("EpisodeId")
            or info.get("episodeId")
            or info.get("episode_id")
        ),
        "seed": info.get("seed") if "seed" in info else replay.get("seed"),
    }
    return {key: value for key, value in candidates.items() if value is not None}


def _aggregate_requested(records: Sequence[Mapping[str, Any]], player: int) -> dict[str, Any]:
    totals: collections.Counter[str] = collections.Counter()
    first_step: dict[str, int] = {}
    by_day: dict[int, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    for record in records:
        day = int(record["day"])
        for event in record["players"][str(player)]["economic_events"]:
            key = _event_key(event)
            quantity = float(event["quantity"])
            totals[key] += quantity
            by_day[day][key] += quantity
            first_step.setdefault(key, int(record["step"]))
    return {
        "totals": dict(sorted(totals.items())),
        "first_step": dict(sorted(first_step.items())),
        "by_day": {
            str(day): dict(sorted(counter.items()))
            for day, counter in sorted(by_day.items())
        },
    }


def _seed_timing(records: Sequence[Mapping[str, Any]], player: int) -> dict[str, Any]:
    queues: dict[str, collections.deque[list[float]]] = collections.defaultdict(collections.deque)
    lags: dict[str, list[int]] = collections.defaultdict(list)
    unmatched_plants: collections.Counter[str] = collections.Counter()
    bought: collections.Counter[str] = collections.Counter()
    planted: collections.Counter[str] = collections.Counter()
    for record in records:
        step = int(record["step"])
        for event in record["players"][str(player)]["economic_events"]:
            crop = event.get("item")
            if not crop:
                continue
            quantity = float(event["quantity"])
            if event["op"] == "BUY_SEED":
                bought[crop] += quantity
                if quantity > 0:
                    queues[crop].append([float(step), quantity])
            elif event["op"] == "PLANT":
                planted[crop] += quantity
                remaining = quantity
                while remaining > 0 and queues[crop]:
                    source_step, available = queues[crop][0]
                    taken = min(remaining, available)
                    whole = int(taken)
                    lags[crop].extend([step - int(source_step)] * whole)
                    if taken - whole > 0:
                        lags[crop].append(step - int(source_step))
                    remaining -= taken
                    available -= taken
                    if available <= 0:
                        queues[crop].popleft()
                    else:
                        queues[crop][0][1] = available
                if remaining > 0:
                    unmatched_plants[crop] += remaining
    crops = sorted(set(bought) | set(planted) | set(queues) | set(unmatched_plants))
    result: dict[str, Any] = {}
    for crop in crops:
        values = lags.get(crop, [])
        unmatched_buys = sum(entry[1] for entry in queues.get(crop, ()))
        result[crop] = {
            "requested_seed_buys": bought[crop],
            "requested_plants": planted[crop],
            "matched_units": len(values),
            "unmatched_plant_units": unmatched_plants[crop],
            "unmatched_buy_units": unmatched_buys,
            "lag_steps_min": min(values) if values else None,
            "lag_steps_max": max(values) if values else None,
            "lag_steps_mean": (sum(values) / len(values)) if values else None,
        }
    return result


def _terminal_name(state: Mapping[str, Any], fallback: str) -> str:
    info = state.get("info")
    if isinstance(info, dict):
        for key in ("name", "agentName", "submissionName", "teamName"):
            if info.get(key):
                return str(info[key])
    return fallback


def analyze_replay(
    replay: Mapping[str, Any],
    provenance: Mapping[str, Any],
    envelope_path: Sequence[str],
    player_a: int,
    player_b: int,
) -> dict[str, Any]:
    steps, player_count = validate_replay(replay)
    if player_a == player_b:
        raise ReplayError("player_a and player_b must be distinct")
    if not (0 <= player_a < player_count and 0 <= player_b < player_count):
        raise ReplayError(f"selected players must be in [0, {player_count - 1}]")

    selected = (player_a, player_b)
    snapshots: dict[int, list[dict[str, Any]]] = {p: [] for p in selected}
    shared_mismatches: list[dict[str, Any]] = []
    for step_index, step in enumerate(steps):
        digests = [
            _shared_digest(_observation(step, p, step_index)) for p in range(player_count)
        ]
        if len(set(digests)) != 1:
            shared_mismatches.append({"step": step_index, "digests": digests})
        for player in selected:
            snapshots[player].append(
                _snapshot(
                    _observation(step, player, step_index),
                    player,
                    f"steps[{step_index}][{player}].observation",
                )
            )

    records: list[dict[str, Any]] = []
    for step_index in range(len(steps) - 1):
        step = steps[step_index]
        record: dict[str, Any] = {
            "step": step_index,
            "day": snapshots[player_a][step_index]["day"],
            "hour": snapshots[player_a][step_index]["hour"],
            "players": {},
        }
        for player in selected:
            before = snapshots[player][step_index]
            after = snapshots[player][step_index + 1]
            events = _action_events(
                step[player].get("action"), f"steps[{step_index}][{player}].action"
            )
            economic = _economic_events(events)
            before_proxy, before_unresolved = _liquid_proxy(before)
            after_proxy, after_unresolved = _liquid_proxy(after)
            record["players"][str(player)] = {
                "action_sha256": _sha256(_canonical_json_bytes(step[player].get("action"))),
                "economic_events": economic,
                "economic_signature": [
                    [
                        event["surface"],
                        event["op"],
                        event.get("item"),
                        event["quantity"],
                    ]
                    for event in economic
                ],
                "before": before,
                "after": after,
                "realized_delta": {
                    "cash": after["cash"] - before["cash"],
                    "hands": after["hands"] - before["hands"],
                    "quadrants": after["quadrants"] - before["quadrants"],
                    "shed": _mapping_delta(after["shed"], before["shed"]),
                    "seeds": _mapping_delta(after["seeds"], before["seeds"]),
                    "carried": _mapping_delta(after["carried"], before["carried"]),
                    "tiles": _integer_mapping_delta(after["tiles"], before["tiles"]),
                    "tile_yield_units": _mapping_delta(
                        after["tile_yield_units"], before["tile_yield_units"]
                    ),
                },
                "liquid_proxy_before": before_proxy,
                "liquid_proxy_after": after_proxy,
                "liquid_proxy_unresolved_items": sorted(
                    set(before_unresolved) | set(after_unresolved)
                ),
            }
        a = record["players"][str(player_a)]
        b = record["players"][str(player_b)]
        record["comparison"] = {
            "cash_gap_before_a_minus_b": a["before"]["cash"] - b["before"]["cash"],
            "cash_gap_after_a_minus_b": a["after"]["cash"] - b["after"]["cash"],
            "cash_gap_swing": (
                a["after"]["cash"]
                - b["after"]["cash"]
                - a["before"]["cash"]
                + b["before"]["cash"]
            ),
            "liquid_proxy_gap_after_a_minus_b": (
                a["liquid_proxy_after"] - b["liquid_proxy_after"]
            ),
            "economic_signatures_equal": (
                a["economic_signature"] == b["economic_signature"]
            ),
        }
        records.append(record)

    requested = {
        str(player): _aggregate_requested(records, player) for player in selected
    }
    timing = {str(player): _seed_timing(records, player) for player in selected}
    keys = set(requested[str(player_a)]["totals"]) | set(
        requested[str(player_b)]["totals"]
    )
    program_delta = {
        key: requested[str(player_a)]["totals"].get(key, 0.0)
        - requested[str(player_b)]["totals"].get(key, 0.0)
        for key in sorted(keys)
        if requested[str(player_a)]["totals"].get(key, 0.0)
        != requested[str(player_b)]["totals"].get(key, 0.0)
    }
    first_divergence = next(
        (
            int(record["step"])
            for record in records
            if not record["comparison"]["economic_signatures_equal"]
        ),
        None,
    )
    top_cash_swings = sorted(
        (
            {
                "step": int(record["step"]),
                "day": int(record["day"]),
                "hour": int(record["hour"]),
                "cash_gap_swing": record["comparison"]["cash_gap_swing"],
                "cash_gap_after_a_minus_b": record["comparison"][
                    "cash_gap_after_a_minus_b"
                ],
            }
            for record in records
            if record["comparison"]["cash_gap_swing"] != 0
        ),
        key=lambda row: (-abs(float(row["cash_gap_swing"])), row["step"]),
    )[:25]

    terminal = steps[-1]
    terminal_summary: dict[str, Any] = {}
    for player in selected:
        state = terminal[player]
        reward = state.get("reward")
        if reward is not None:
            reward = _numeric(reward, f"terminal[{player}].reward")
        terminal_summary[str(player)] = {
            "name": _terminal_name(state, f"player_{player}"),
            "status": state.get("status"),
            "reward": reward,
            "cash": snapshots[player][-1]["cash"],
            "shed": snapshots[player][-1]["shed"],
            "seeds": snapshots[player][-1]["seeds"],
            "tiles": snapshots[player][-1]["tiles"],
            "hands": snapshots[player][-1]["hands"],
            "quadrants": snapshots[player][-1]["quadrants"],
        }

    day_zero_delta = {
        key: requested[str(player_a)]["by_day"].get("0", {}).get(key, 0.0)
        - requested[str(player_b)]["by_day"].get("0", {}).get(key, 0.0)
        for key in sorted(
            set(requested[str(player_a)]["by_day"].get("0", {}))
            | set(requested[str(player_b)]["by_day"].get("0", {}))
        )
        if requested[str(player_a)]["by_day"].get("0", {}).get(key, 0.0)
        != requested[str(player_b)]["by_day"].get("0", {}).get(key, 0.0)
    }

    return {
        "schema": SCHEMA,
        "source": {
            **dict(provenance),
            "envelope_path": list(envelope_path),
            "canonical_replay_sha256": _sha256(_canonical_json_bytes(replay)),
            **_identity_from_replay(replay),
        },
        "comparison": {
            "player_a": player_a,
            "player_b": player_b,
            "player_count": player_count,
            "state_frames": len(steps),
            "action_steps": len(records),
            "first_economic_signature_divergence_step": first_divergence,
            "program_delta_a_minus_b": program_delta,
            "day_zero_program_delta_a_minus_b": day_zero_delta,
            "top_cash_gap_swings": top_cash_swings,
        },
        "players": {
            str(player): {
                "requested": requested[str(player)],
                "requested_seed_buy_to_plant_timing": timing[str(player)],
                "terminal": terminal_summary[str(player)],
            }
            for player in selected
        },
        "shared_state_mismatches": shared_mismatches,
        "timeline": records,
        "interpretation_boundary": {
            "requested_actions_are_not_execution_receipts": True,
            "state_deltas_can_include_simultaneous_opponent_and_environment_effects": True,
            "liquid_proxy_is_not_the_official_reward": True,
            "single_replay_differences_are_observational_not_causal": True,
            "required_next_step_for_policy_claim": (
                "materialize a one-factor candidate and run identical-seed, both-seat official games"
            ),
        },
    }


def _fmt_number(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float) and value.is_integer():
        return f"{int(value):,}"
    if isinstance(value, (int, float)):
        return f"{value:,.3f}".rstrip("0").rstrip(".")
    return str(value)


def render_markdown(report: Mapping[str, Any]) -> str:
    comparison = report["comparison"]
    a = str(comparison["player_a"])
    b = str(comparison["player_b"])
    pa = report["players"][a]
    pb = report["players"][b]
    lines = [
        "# Kaggriculture replay economic-program differential",
        "",
        f"Schema: `{report['schema']}`",
        f"Canonical replay SHA-256: `{report['source']['canonical_replay_sha256']}`",
        f"Players: **{a}** versus **{b}**; action steps: **{comparison['action_steps']}**.",
        "",
        "## Terminal observation",
        "",
        "| Player | Name | Reward | Cash | Hands | Quadrants |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for key, player in ((a, pa), (b, pb)):
        terminal = player["terminal"]
        lines.append(
            "| {key} | {name} | {reward} | {cash} | {hands} | {quadrants} |".format(
                key=key,
                name=str(terminal["name"]).replace("|", "\\|"),
                reward=_fmt_number(terminal["reward"]),
                cash=_fmt_number(terminal["cash"]),
                hands=terminal["hands"],
                quadrants=terminal["quadrants"],
            )
        )
    lines.extend(
        [
            "",
            "## Program divergence",
            "",
            f"First unequal economic action signature: step **{_fmt_number(comparison['first_economic_signature_divergence_step'])}**.",
            "",
            "Positive quantities below mean player A requested more; negative quantities mean player B requested more.",
            "",
            "| Requested operation | A − B | Day 0 A − B |",
            "|---|---:|---:|",
        ]
    )
    all_keys = sorted(
        set(comparison["program_delta_a_minus_b"])
        | set(comparison["day_zero_program_delta_a_minus_b"])
    )
    for key in all_keys:
        lines.append(
            f"| `{key}` | {_fmt_number(comparison['program_delta_a_minus_b'].get(key, 0))} | "
            f"{_fmt_number(comparison['day_zero_program_delta_a_minus_b'].get(key, 0))} |"
        )
    if not all_keys:
        lines.append("| _none_ | 0 | 0 |")

    lines.extend(["", "## Requested seed buy-to-plant timing", ""])
    crops = sorted(
        set(pa["requested_seed_buy_to_plant_timing"])
        | set(pb["requested_seed_buy_to_plant_timing"])
    )
    lines.extend(
        [
            "| Crop | Player | Buys | Plants | Mean lag (steps) | Max lag | Unmatched buys |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for crop in crops:
        for key, player in ((a, pa), (b, pb)):
            row = player["requested_seed_buy_to_plant_timing"].get(crop, {})
            lines.append(
                f"| {crop} | {key} | {_fmt_number(row.get('requested_seed_buys', 0))} | "
                f"{_fmt_number(row.get('requested_plants', 0))} | "
                f"{_fmt_number(row.get('lag_steps_mean'))} | "
                f"{_fmt_number(row.get('lag_steps_max'))} | "
                f"{_fmt_number(row.get('unmatched_buy_units', 0))} |"
            )
    if not crops:
        lines.append("| _none_ | — | 0 | 0 | — | — | 0 |")

    lines.extend(["", "## Largest cash-gap swings", ""])
    lines.extend(
        [
            "| Step | Day | Hour | Gap swing (A − B) | Gap after |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for row in comparison["top_cash_gap_swings"][:15]:
        lines.append(
            f"| {row['step']} | {row['day']} | {row['hour']} | "
            f"{_fmt_number(row['cash_gap_swing'])} | "
            f"{_fmt_number(row['cash_gap_after_a_minus_b'])} |"
        )
    if not comparison["top_cash_gap_swings"]:
        lines.append("| — | — | — | 0 | 0 |")

    lines.extend(
        [
            "",
            "## Admission boundary",
            "",
            "This report distinguishes returned actions from realized state deltas. "
            "A returned order may fail, and a shared market delta may include the rival, town consumption, or end-of-day refresh. "
            "The liquid proxy is descriptive only. A single replay can generate hypotheses, not a promotion or causal score claim.",
            "",
            "Policy admission requires a one-factor candidate evaluated on identical seeds, opponents, and both seats in the official engine.",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("replay", type=Path, help="raw JSON or gzip replay path")
    parser.add_argument("--player-a", type=int, default=0)
    parser.add_argument("--player-b", type=int, default=1)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-markdown", type=Path)
    parser.add_argument("--expect-episode-id", type=int)
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload, provenance = _read_input(args.replay)
        replay, envelope_path = unwrap_replay(payload)
        report = analyze_replay(
            replay,
            provenance,
            envelope_path,
            args.player_a,
            args.player_b,
        )
        if args.expect_episode_id is not None:
            actual = report["source"].get("episode_id")
            if actual != args.expect_episode_id:
                raise ReplayError(
                    f"episode id mismatch: expected {args.expect_episode_id}, got {actual!r}"
                )
        json_text = json.dumps(
            report,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            indent=None if args.compact else 2,
        ) + "\n"
        markdown = render_markdown(report)
        if args.output_json:
            args.output_json.write_text(json_text, encoding="utf-8")
        else:
            sys.stdout.write(json_text)
        if args.output_markdown:
            args.output_markdown.write_text(markdown, encoding="utf-8")
        return 0
    except (OSError, ReplayError) as exc:
        print(f"REPLAY_PROGRAM_DIFF_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
