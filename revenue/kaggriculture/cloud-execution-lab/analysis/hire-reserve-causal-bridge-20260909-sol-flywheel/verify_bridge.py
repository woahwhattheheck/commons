#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify the submitted-replay cash-only HIRE bifurcation receipt.

The raw replay is optional because its custody object lives in Slack.  The
committed receipt is self-bound and exact-value checked.  Supplying ``--replay``
recomputes every fact from the gzip bytes with the Kaggle replay orientation
``action[k] <- observation[k-1]``.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

HERE = Path(__file__).resolve().parent
RECEIPT_PATH = HERE / "BRIDGE.json"
SCHEMA = "titan.hire-reserve-causal-bridge.v1"
INTERPRETATION = (
    "This receipt proves a cash-only own-state twin, exact HIRE affordability "
    "bifurcation, and downstream submitted-action reachability loss in one "
    "identified replay. It does not prove score delta, seed-policy causality, "
    "candidate strength, release readiness, or automatic promotion."
)
MAX_GZIP_BYTES = 5_000_000
MAX_JSON_BYTES = 64_000_000

EXPECTED = {
    "episode_id": 107130860,
    "transport_bytes": 474669,
    "transport_sha256": "9337c7c734eff0804400f732d48c155dedb6d6f12b3afdefbc620f78fdfc686b",
    "json_bytes": 31790508,
    "json_sha256": "468845b1bc00f11a4d4a3deb2cc785a2ee222db31e6a0e88df2d7057f14ec6b1",
    "agents": ["Apa", "Bryce Muhlnickel"],
    "rewards": [127877.0, 114765.0],
    "first_divergence_row": 2,
    "reconvergence_start": 19,
    "reconvergence_end": 24,
    "bridge_observation_row": 24,
    "bridge_action_row": 25,
    "cash": [42.0, 6.0],
    "hire_costs": [1, 1, 2, 3],
    "hires_requested": 4,
    "hires_executed": [4, 3],
    "post_cash": [35.0, 2.0],
    "post_hands": [4, 3],
    "minimum_extra_cash": 1,
    "unreachable_start": 26,
    "unreachable_end": 48,
    "unreachable_rows": 23,
    "unreachable_actions": [
        ["PICKUP", "WHEAT"], ["NORTH"], ["FEED"], ["CARE"],
        ["COLLECT_FERTILIZER"], ["SOUTH"], ["PLACE", "FERTILIZER"],
        ["WEST"], ["CARE"],
        *([["PASS"]] * 14),
    ],
}


class BridgeError(ValueError):
    """Raised when source or receipt bytes violate the closed contract."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise BridgeError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _constant(value: str) -> Any:
    raise BridgeError(f"non-finite JSON constant: {value}")


def strict_loads(data: bytes) -> Any:
    try:
        text = data.decode("utf-8", errors="strict")
        return json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    except UnicodeDecodeError as error:
        raise BridgeError("source is not strict UTF-8") from error
    except json.JSONDecodeError as error:
        raise BridgeError(f"invalid JSON: {error}") from error


def _whole(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BridgeError(f"{label} must be a nonnegative integer")
    return value


def _cash(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BridgeError(f"{label} must be finite numeric cash")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise BridgeError(f"{label} must be finite nonnegative cash")
    return number


def _fib(index: int) -> int:
    index = _whole(index, "Fibonacci index")
    a, b = 1, 1
    for _ in range(index):
        a, b = b, a + b
    return a


def hire_costs(hires_today: int, count: int, multiplier: int = 1) -> list[int]:
    hires_today = _whole(hires_today, "hires_today")
    count = _whole(count, "hire count")
    multiplier = _whole(multiplier, "hire multiplier")
    return [multiplier * _fib(hires_today + offset) for offset in range(count)]


def simulate_hires(cash: float, hires_today: int, requested: int,
                   multiplier: int = 1) -> dict[str, Any]:
    remaining = _cash(cash, "cash")
    costs = hire_costs(hires_today, requested, multiplier)
    executed = 0
    paid: list[int] = []
    for cost in costs:
        if remaining < cost:
            break
        remaining -= cost
        paid.append(cost)
        executed += 1
    return {
        "requested": requested,
        "executed": executed,
        "costs": costs,
        "paid": paid,
        "spent": float(sum(paid)),
        "remaining_cash": float(remaining),
    }


def minimum_cash_for_hires(hires_today: int, count: int,
                           multiplier: int = 1) -> int:
    return sum(hire_costs(hires_today, count, multiplier))


def _record(document: Mapping[str, Any], row: int, seat: int) -> Mapping[str, Any]:
    steps = document.get("steps")
    if not isinstance(steps, list) or not (0 <= row < len(steps)):
        raise BridgeError("row outside replay")
    frame = steps[row]
    if not isinstance(frame, list) or not (0 <= seat < len(frame)):
        raise BridgeError("seat outside replay frame")
    record = frame[seat]
    if not isinstance(record, dict):
        raise BridgeError("malformed replay record")
    return record


def _observation(document: Mapping[str, Any], row: int, seat: int) -> Mapping[str, Any]:
    observation = _record(document, row, seat).get("observation")
    if not isinstance(observation, dict):
        raise BridgeError("missing replay observation")
    if observation.get("player") != seat:
        raise BridgeError("observation player does not match seat")
    return observation


def _action(document: Mapping[str, Any], row: int, seat: int) -> Mapping[str, Any]:
    action = _record(document, row, seat).get("action")
    if not isinstance(action, dict):
        raise BridgeError("missing replay action")
    if not isinstance(action.get("hands", []), list):
        raise BridgeError("action hands must be a list")
    if not isinstance(action.get("market", []), list):
        raise BridgeError("action market must be a list")
    return action


def _own_farm(observation: Mapping[str, Any], seat: int) -> Mapping[str, Any]:
    farms = observation.get("farms")
    if not isinstance(farms, list) or seat >= len(farms) or not isinstance(farms[seat], dict):
        raise BridgeError("missing own farm")
    return farms[seat]


def own_state(observation: Mapping[str, Any], seat: int, *, include_cash: bool) -> dict[str, Any]:
    farm = copy.deepcopy(dict(_own_farm(observation, seat)))
    if not include_cash:
        farm.pop("money", None)
    private = observation.get("private")
    if not isinstance(private, dict):
        raise BridgeError("missing private state")
    return {"farm": farm, "private": copy.deepcopy(private)}


def own_state_digest(observation: Mapping[str, Any], seat: int, *, include_cash: bool) -> str:
    return sha256(canonical_bytes(own_state(observation, seat, include_cash=include_cash)))


def actions_equal(document: Mapping[str, Any], row: int) -> bool:
    return canonical_bytes(_action(document, row, 0)) == canonical_bytes(_action(document, row, 1))


def own_noncash_equal(document: Mapping[str, Any], row: int) -> bool:
    left = own_state(_observation(document, row, 0), 0, include_cash=False)
    right = own_state(_observation(document, row, 1), 1, include_cash=False)
    return canonical_bytes(left) == canonical_bytes(right)


def _market_quantity(action: Mapping[str, Any]) -> dict[tuple[str, str], int]:
    quantities: dict[tuple[str, str], int] = {}
    for order in action.get("market", []):
        if not isinstance(order, list) or not order:
            continue
        op = order[0]
        if not isinstance(op, str):
            raise BridgeError("market opcode must be text")
        item = order[1] if len(order) > 1 and isinstance(order[1], str) else ""
        if op in ("HIRE", "BUY_LAND"):
            quantity = 1
        elif len(order) > 2:
            quantity = _whole(order[2], "market quantity")
        else:
            quantity = 0
        key = (op, item)
        quantities[key] = quantities.get(key, 0) + quantity
    return quantities


def first_action_divergence(document: Mapping[str, Any]) -> dict[str, Any]:
    steps = document.get("steps")
    if not isinstance(steps, list):
        raise BridgeError("steps must be a list")
    for row in range(1, len(steps)):
        left, right = _action(document, row, 0), _action(document, row, 1)
        if canonical_bytes(left) == canonical_bytes(right):
            continue
        q0, q1 = _market_quantity(left), _market_quantity(right)
        keys = sorted(set(q0) | set(q1))
        delta = [
            {"op": op, "item": item, "seat0": q0.get((op, item), 0),
             "seat1": q1.get((op, item), 0),
             "seat1_minus_seat0": q1.get((op, item), 0) - q0.get((op, item), 0)}
            for op, item in keys if q0.get((op, item), 0) != q1.get((op, item), 0)
        ]
        return {
            "action_row": row,
            "selected_from_observation_row": row - 1,
            "seat0_market": copy.deepcopy(left.get("market", [])),
            "seat1_market": copy.deepcopy(right.get("market", [])),
            "market_quantity_delta": delta,
            "action_sha256": [sha256(canonical_bytes(left)), sha256(canonical_bytes(right))],
        }
    raise BridgeError("replay has no action divergence")


def _isolated_hire_count(action: Mapping[str, Any], maximum: int) -> int | None:
    market = action.get("market")
    if not isinstance(market, list):
        return None
    count = 0
    for order in market[:maximum]:
        if order in (None, [], ["PASS"]):
            continue
        if not isinstance(order, list) or order != ["HIRE"]:
            return None
        count += 1
    return count if count else None


def _observed_cash_and_hands(document: Mapping[str, Any], row: int, seat: int) -> tuple[float, int, int]:
    observation = _observation(document, row, seat)
    farm = _own_farm(observation, seat)
    hands = farm.get("hands")
    if not isinstance(hands, list):
        raise BridgeError("farm hands must be a list")
    return (_cash(farm.get("money"), "farm money"), len(hands),
            _whole(farm.get("hires_today"), "hires_today"))


def _unreachable_block(document: Mapping[str, Any], seat: int, start_row: int) -> dict[str, Any]:
    steps = document.get("steps")
    if not isinstance(steps, list):
        raise BridgeError("steps must be a list")
    rows: list[dict[str, Any]] = []
    for row in range(start_row, len(steps)):
        previous = _observation(document, row - 1, seat)
        available = len(_own_farm(previous, seat).get("hands", []))
        submitted = _action(document, row, seat).get("hands", [])
        if len(submitted) <= available:
            break
        extras = submitted[available:]
        if not all(isinstance(action, list) and action and isinstance(action[0], str)
                   for action in extras):
            raise BridgeError("malformed unreachable hand action")
        rows.append({
            "action_row": row,
            "selected_from_observation_row": row - 1,
            "observable_hands": available,
            "submitted_hand_rows": len(submitted),
            "unreachable": copy.deepcopy(extras),
        })
    if not rows:
        raise BridgeError("expected downstream unreachable block")
    return {
        "seat": seat,
        "start_action_row": rows[0]["action_row"],
        "end_action_row": rows[-1]["action_row"],
        "rows": len(rows),
        "unreachable_actions": [entry["unreachable"][0] for entry in rows],
        "unreachable_actions_sha256": sha256(canonical_bytes(
            [entry["unreachable"][0] for entry in rows]
        )),
        "detail": rows,
    }


def _validate_document(document: Mapping[str, Any]) -> None:
    if not isinstance(document, dict):
        raise BridgeError("replay root must be an object")
    steps = document.get("steps")
    if not isinstance(steps, list) or len(steps) < 2:
        raise BridgeError("replay must contain multiple steps")
    configuration = document.get("configuration")
    if not isinstance(configuration, dict):
        raise BridgeError("missing configuration")
    for row, frame in enumerate(steps):
        if not isinstance(frame, list) or len(frame) != 2:
            raise BridgeError(f"row {row} is not a two-seat frame")
        for seat in (0, 1):
            _observation(document, row, seat)
            _action(document, row, seat)


def _agent_names(document: Mapping[str, Any]) -> list[str]:
    info = document.get("info")
    if not isinstance(info, dict) or not isinstance(info.get("Agents"), list):
        raise BridgeError("missing agent metadata")
    names = []
    for agent in info["Agents"]:
        if not isinstance(agent, dict) or not isinstance(agent.get("Name"), str):
            raise BridgeError("malformed agent metadata")
        names.append(agent["Name"])
    return names


def _episode_id(document: Mapping[str, Any]) -> int:
    info = document.get("info")
    value = info.get("EpisodeId") if isinstance(info, dict) else None
    return _whole(value, "episode id")


def _find_bridge(document: Mapping[str, Any]) -> dict[str, Any]:
    cfg = document["configuration"]
    maximum = _whole(cfg.get("maxMarketOrdersPerTurn", 10), "market order limit")
    multiplier = _whole(cfg.get("farmHandCostMult", 1), "hire multiplier")
    steps = document["steps"]

    for action_row in range(1, len(steps)):
        observation_row = action_row - 1
        if not actions_equal(document, action_row):
            continue
        if not own_noncash_equal(document, observation_row):
            continue
        action = _action(document, action_row, 0)
        requested = _isolated_hire_count(action, maximum)
        if requested is None:
            continue
        before = [_observed_cash_and_hands(document, observation_row, seat)
                  for seat in (0, 1)]
        if before[0][1:] != before[1][1:] or before[0][0] == before[1][0]:
            continue
        simulations = [simulate_hires(item[0], item[2], requested, multiplier)
                       for item in before]
        if simulations[0]["executed"] == simulations[1]["executed"]:
            continue
        after = [_observed_cash_and_hands(document, action_row, seat)
                 for seat in (0, 1)]
        for seat in (0, 1):
            expected_hands = before[seat][1] + simulations[seat]["executed"]
            if after[seat][1] != expected_hands:
                raise BridgeError("observed hand count does not match isolated HIRE replay")
            if after[seat][0] != simulations[seat]["remaining_cash"]:
                raise BridgeError("observed cash does not match isolated HIRE replay")
        rich = max((0, 1), key=lambda seat: simulations[seat]["executed"])
        poor = 1 - rich
        target = simulations[rich]["executed"]
        required = minimum_cash_for_hires(before[poor][2], target, multiplier)
        shortfall = max(0, required - int(before[poor][0]))
        block = _unreachable_block(document, poor, action_row + 1)
        return {
            "observation_row": observation_row,
            "action_row": action_row,
            "selected_action_sha256": sha256(canonical_bytes(action)),
            "selected_action": copy.deepcopy(action),
            "hires_requested": requested,
            "hire_multiplier": multiplier,
            "hire_costs": hire_costs(before[0][2], requested, multiplier),
            "cash_before": [before[0][0], before[1][0]],
            "hands_before": [before[0][1], before[1][1]],
            "hires_today_before": [before[0][2], before[1][2]],
            "hires_executed": [simulations[0]["executed"], simulations[1]["executed"]],
            "cash_after": [after[0][0], after[1][0]],
            "hands_after": [after[0][1], after[1][1]],
            "rich_seat": rich,
            "constrained_seat": poor,
            "minimum_cash_for_rich_execution": required,
            "minimum_extra_cash_for_constrained_seat": shortfall,
            "own_noncash_state_sha256": own_state_digest(
                _observation(document, observation_row, 0), 0, include_cash=False
            ),
            "downstream": block,
        }
    raise BridgeError("no cash-only isolated HIRE bifurcation found")


def _reconvergence(document: Mapping[str, Any], bridge_observation_row: int) -> dict[str, Any]:
    if not own_noncash_equal(document, bridge_observation_row):
        raise BridgeError("bridge row is not a cash-only twin")
    start = bridge_observation_row
    while start > 0 and own_noncash_equal(document, start - 1):
        start -= 1
    end = bridge_observation_row
    steps = document["steps"]
    while end + 1 < len(steps) and own_noncash_equal(document, end + 1):
        end += 1
    rows = []
    for row in range(start, bridge_observation_row + 1):
        cash = [_observed_cash_and_hands(document, row, seat)[0] for seat in (0, 1)]
        rows.append({"observation_row": row, "cash": cash,
                     "cash_gap_seat0_minus_seat1": cash[0] - cash[1]})
    return {
        "start_observation_row": start,
        "end_observation_row": end,
        "through_bridge_row": bridge_observation_row,
        "rows_through_bridge": rows,
        "state_sha256_at_bridge": own_state_digest(
            _observation(document, bridge_observation_row, 0), 0, include_cash=False
        ),
    }


def audit_document(document: Mapping[str, Any], *, source: Mapping[str, Any]) -> dict[str, Any]:
    _validate_document(document)
    bridge = _find_bridge(document)
    first = first_action_divergence(document)
    reconvergence = _reconvergence(document, bridge["observation_row"])
    names = _agent_names(document)
    rewards = document.get("rewards")
    if not isinstance(rewards, list) or len(rewards) != 2:
        raise BridgeError("missing two-seat rewards")

    melon_delta = next((entry for entry in first["market_quantity_delta"]
                        if entry["op"] == "BUY_SEED" and entry["item"] == "MELON"), None)
    if melon_delta is None:
        raise BridgeError("first divergence has no MELON seed delta")
    seed_price = 80
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "automatic_promotion": False,
        "interpretation": INTERPRETATION,
        "source": dict(source),
        "episode": {
            "episode_id": _episode_id(document),
            "agents": names,
            "rewards": [float(rewards[0]), float(rewards[1])],
            "steps": len(document["steps"]),
            "turns_per_day": _whole(document["configuration"].get("turnsPerDay", 24),
                                     "turns per day"),
        },
        "upstream_program_marker": {
            **first,
            "seat1_extra_melon_seed_units": melon_delta["seat1_minus_seat0"],
            "canonical_melon_seed_unit_cost": seed_price,
            "gross_extra_melon_seed_commitment": (
                melon_delta["seat1_minus_seat0"] * seed_price
            ),
            "claim_scope": (
                "Marker only: later market actions also differ, so this receipt does "
                "not attribute the bridge cash gap solely to this seed order."
            ),
        },
        "cash_only_reconvergence": reconvergence,
        "hire_bridge": bridge,
        "candidate_target": {
            "preserve_cash_by_observation_row": bridge["observation_row"],
            "minimum_cash": bridge["minimum_cash_for_rich_execution"],
            "minimum_extra_cash": bridge["minimum_extra_cash_for_constrained_seat"],
            "restored_hands": (
                bridge["hires_executed"][bridge["rich_seat"]]
                - bridge["hires_executed"][bridge["constrained_seat"]]
            ),
            "submitted_rows_made_reachable": bridge["downstream"]["rows"],
            "policy_requirement": (
                "Any source candidate must preserve the represented seed/production "
                "commitments and prove the reserve without forecasting rival receipts."
            ),
            "requires_paired_official_panel": True,
        },
    }
    report["report_sha256"] = sha256(canonical_bytes(report))
    return report


def load_replay(path: Path) -> tuple[Mapping[str, Any], dict[str, Any]]:
    raw = path.read_bytes()
    if len(raw) > MAX_GZIP_BYTES:
        raise BridgeError("gzip source exceeds bound")
    try:
        decoded = gzip.decompress(raw)
    except (gzip.BadGzipFile, EOFError, OSError) as error:
        raise BridgeError("invalid gzip source") from error
    if len(decoded) > MAX_JSON_BYTES:
        raise BridgeError("decoded JSON exceeds bound")
    document = strict_loads(decoded)
    return document, {
        "filename": path.name,
        "slack_file_id": "F0C0KEQ5MFY",
        "transport_bytes": len(raw),
        "transport_sha256": sha256(raw),
        "json_bytes": len(decoded),
        "json_sha256": sha256(decoded),
    }


def seal(value: Mapping[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(dict(value))
    out.pop("report_sha256", None)
    out["report_sha256"] = sha256(canonical_bytes(out))
    return out


def _expect(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BridgeError(f"{label} differs: {actual!r} != {expected!r}")


def _mechanics_contract() -> None:
    """When checked out in Commons, bind our costs to current extracted mechanics."""
    mechanics_path = HERE.parents[1] / "mechanics.py"
    if not mechanics_path.is_file():
        return
    spec = importlib.util.spec_from_file_location("_sol_flywheel_mechanics", mechanics_path)
    if spec is None or spec.loader is None:
        raise BridgeError("cannot load canonical mechanics")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    actual = [module._hire_cost(index, 1) for index in range(4)]
    _expect(actual, EXPECTED["hire_costs"], "canonical mechanics hire costs")
    _expect(module.CROPS["MELON"]["seed"], 80, "canonical MELON seed cost")


def verify_receipt(receipt: Mapping[str, Any]) -> tuple[bool, str]:
    try:
        if not isinstance(receipt, dict):
            raise BridgeError("receipt root must be an object")
        _expect(receipt.get("schema"), SCHEMA, "schema")
        _expect(receipt.get("automatic_promotion"), False, "automatic_promotion")
        _expect(receipt.get("interpretation"), INTERPRETATION, "interpretation")
        claimed = receipt.get("report_sha256")
        _expect(claimed, seal(receipt)["report_sha256"], "report SHA-256")

        source = receipt.get("source", {})
        episode = receipt.get("episode", {})
        marker = receipt.get("upstream_program_marker", {})
        recon = receipt.get("cash_only_reconvergence", {})
        bridge = receipt.get("hire_bridge", {})
        downstream = bridge.get("downstream", {})
        target = receipt.get("candidate_target", {})

        for key in ("transport_bytes", "transport_sha256", "json_bytes", "json_sha256"):
            _expect(source.get(key), EXPECTED[key], f"source {key}")
        _expect(source.get("slack_file_id"), "F0C0KEQ5MFY", "Slack file ID")
        _expect(episode.get("episode_id"), EXPECTED["episode_id"], "episode id")
        _expect(episode.get("agents"), EXPECTED["agents"], "agents")
        _expect(episode.get("rewards"), EXPECTED["rewards"], "rewards")
        _expect(episode.get("steps"), 720, "step count")
        _expect(episode.get("turns_per_day"), 24, "turns per day")

        _expect(marker.get("action_row"), EXPECTED["first_divergence_row"],
                "first divergence row")
        _expect(marker.get("selected_from_observation_row"), 1,
                "first divergence orientation")
        _expect(marker.get("seat1_extra_melon_seed_units"), 12,
                "MELON seed delta")
        _expect(marker.get("canonical_melon_seed_unit_cost"), 80,
                "MELON seed price")
        _expect(marker.get("gross_extra_melon_seed_commitment"), 960,
                "MELON seed commitment")

        _expect(recon.get("start_observation_row"), EXPECTED["reconvergence_start"],
                "reconvergence start")
        _expect(recon.get("end_observation_row"), EXPECTED["reconvergence_end"],
                "reconvergence end")
        _expect(recon.get("through_bridge_row"), EXPECTED["bridge_observation_row"],
                "reconvergence bridge row")
        final_cash = recon.get("rows_through_bridge", [])[-1].get("cash")
        _expect(final_cash, EXPECTED["cash"], "bridge cash twin")

        _expect(bridge.get("observation_row"), EXPECTED["bridge_observation_row"],
                "bridge observation row")
        _expect(bridge.get("action_row"), EXPECTED["bridge_action_row"],
                "bridge action row")
        _expect(bridge.get("hires_requested"), EXPECTED["hires_requested"],
                "requested hires")
        _expect(bridge.get("hire_costs"), EXPECTED["hire_costs"], "hire costs")
        _expect(bridge.get("cash_before"), EXPECTED["cash"], "cash before")
        _expect(bridge.get("hires_executed"), EXPECTED["hires_executed"],
                "executed hires")
        _expect(bridge.get("cash_after"), EXPECTED["post_cash"], "cash after")
        _expect(bridge.get("hands_after"), EXPECTED["post_hands"], "hands after")
        _expect(bridge.get("rich_seat"), 0, "rich seat")
        _expect(bridge.get("constrained_seat"), 1, "constrained seat")
        _expect(bridge.get("minimum_cash_for_rich_execution"), 7,
                "minimum cash for four hires")
        _expect(bridge.get("minimum_extra_cash_for_constrained_seat"),
                EXPECTED["minimum_extra_cash"], "minimum reserve gap")

        _expect(downstream.get("seat"), 1, "downstream seat")
        _expect(downstream.get("start_action_row"), EXPECTED["unreachable_start"],
                "unreachable start")
        _expect(downstream.get("end_action_row"), EXPECTED["unreachable_end"],
                "unreachable end")
        _expect(downstream.get("rows"), EXPECTED["unreachable_rows"],
                "unreachable rows")
        _expect(downstream.get("unreachable_actions"), EXPECTED["unreachable_actions"],
                "unreachable actions")

        _expect(target.get("minimum_extra_cash"), 1, "candidate target cash")
        _expect(target.get("restored_hands"), 1, "candidate target hands")
        _expect(target.get("submitted_rows_made_reachable"), 23,
                "candidate target rows")
        _expect(target.get("requires_paired_official_panel"), True,
                "paired-panel requirement")
        _mechanics_contract()
        return True, "verified"
    except (BridgeError, IndexError, KeyError, TypeError) as error:
        return False, str(error)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", type=Path,
                        help="optional exact 107130860.json.gz custody object")
    parser.add_argument("--write-receipt", action="store_true",
                        help="write the recomputed report to BRIDGE.json")
    args = parser.parse_args(argv)

    receipt = strict_loads(RECEIPT_PATH.read_bytes()) if RECEIPT_PATH.exists() else None
    if args.replay is not None:
        document, source = load_replay(args.replay)
        recomputed = audit_document(document, source=source)
        valid, detail = verify_receipt(recomputed)
        if not valid:
            raise BridgeError("recomputed replay report failed contract: " + detail)
        if receipt is not None and canonical_bytes(recomputed) != canonical_bytes(receipt):
            raise BridgeError("committed receipt differs from exact replay reproduction")
        if args.write_receipt:
            RECEIPT_PATH.write_bytes(json.dumps(recomputed, indent=2, sort_keys=True,
                                                ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n")
        mode = "manifest+replay"
        chosen = recomputed
    else:
        if receipt is None:
            raise BridgeError("BRIDGE.json is missing")
        valid, detail = verify_receipt(receipt)
        if not valid:
            raise BridgeError(detail)
        mode = "manifest"
        chosen = receipt

    bridge = chosen["hire_bridge"]
    downstream = bridge["downstream"]
    print(
        "PASS mode={} episode={} cash={}/{} hire={}/{} shortfall=${} "
        "unreachable_rows={} report_sha256={}".format(
            mode, chosen["episode"]["episode_id"],
            int(bridge["cash_before"][0]), int(bridge["cash_before"][1]),
            bridge["hires_executed"][0], bridge["hires_executed"][1],
            bridge["minimum_extra_cash_for_constrained_seat"], downstream["rows"],
            chosen["report_sha256"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
