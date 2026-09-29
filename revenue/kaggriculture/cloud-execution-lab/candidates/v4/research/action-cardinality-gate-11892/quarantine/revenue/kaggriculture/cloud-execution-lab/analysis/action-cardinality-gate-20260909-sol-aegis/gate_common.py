#!/usr/bin/env python3
"""Fail-closed Kaggriculture replay gate for observable hand/action cardinality.

The Kaggle replay contract records the action selected from observation k-1 on
step k.  Step zero is the sole bootstrap exception and is evaluated against its
own initial observation.  This module rejects a replay whenever an action
contains more hired-hand rows than the acting player could observe immediately
before that action.

This is a release-integrity gate, not a playing-strength evaluator.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

GATE_ID = "titan-v3-observable-hand-action-cardinality"
SCHEMA_VERSION = 1
MAX_REPLAY_BYTES = 64 * 1024 * 1024
CANONICAL_MARKET_NO_ORDER = ["SELL", "WHEAT", 0]
EXIT_PASS = 0
EXIT_REJECT = 2
EXIT_INVALID = 3
EXIT_RECEIPT_TAMPERED = 4


class GateInputError(ValueError):
    """Raised when evidence is absent, ambiguous, or malformed."""


def _exact_int(value: Any, label: str, *, minimum: int | None = None) -> int:
    if type(value) is not int:  # deliberately rejects bool
        raise GateInputError(f"{label} must be an exact integer")
    if minimum is not None and value < minimum:
        raise GateInputError(f"{label} must be >= {minimum}")
    return value


def _exact_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise GateInputError(f"{label} must be a non-empty string")
    return value


def canonical_json_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise GateInputError(f"value is not canonical JSON: {exc}") from exc
    return text.encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


IMPLEMENTATION_FILES = (
    "action_cardinality_gate.py",
    "gate_common.py",
    "gate_core.py",
    "gate_receipt.py",
)


def _tool_sha256() -> str:
    """Hash the complete executable implementation, not only the CLI facade."""
    try:
        directory = Path(__file__).resolve().parent
        inventory = []
        for name in IMPLEMENTATION_FILES:
            payload = (directory / name).read_bytes()
            inventory.append(
                {"path": name, "bytes": len(payload), "sha256": sha256_bytes(payload)}
            )
        return sha256_bytes(canonical_json_bytes(inventory))
    except OSError as exc:
        raise GateInputError(f"cannot hash gate implementation: {exc}") from exc


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise GateInputError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise GateInputError(f"{label} must be an array")
    return value


def _require_key(mapping: Mapping[str, Any], key: str, label: str) -> Any:
    if key not in mapping:
        raise GateInputError(f"{label}.{key} is absent")
    return mapping[key]


def _validate_action_rows(rows: list[Any], label: str) -> None:
    for index, row in enumerate(rows):
        if not isinstance(row, list) or not row:
            raise GateInputError(f"{label}[{index}] must be a non-empty action row")
        _exact_string(row[0], f"{label}[{index}][0]")


def _is_canonical_market_no_order(row: Any) -> bool:
    return (
        isinstance(row, list)
        and len(row) == 3
        and row[0] == "SELL"
        and row[1] == "WHEAT"
        and type(row[2]) is int
        and row[2] == 0
    )


def _opcode(row: Any) -> str:
    if not isinstance(row, list) or not row or not isinstance(row[0], str):
        return "<MALFORMED>"
    op = row[0]
    if op in {"NORTH", "SOUTH", "EAST", "WEST"}:
        return "MOVE"
    return op


def _read_replay_bytes(path: Path) -> tuple[bytes, bytes, str]:
    try:
        stat = path.stat()
    except OSError as exc:
        raise GateInputError(f"cannot stat replay: {exc}") from exc
    if stat.st_size <= 0:
        raise GateInputError("replay is empty")
    if stat.st_size > MAX_REPLAY_BYTES:
        raise GateInputError(
            f"replay exceeds {MAX_REPLAY_BYTES} byte input ceiling: {stat.st_size}"
        )
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise GateInputError(f"cannot read replay: {exc}") from exc
    raw_sha256 = sha256_bytes(raw)
    if raw.startswith(b"\x1f\x8b"):
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(raw), mode="rb") as handle:
                decoded = handle.read(MAX_REPLAY_BYTES + 1)
        except (OSError, EOFError) as exc:
            raise GateInputError(f"invalid gzip replay: {exc}") from exc
        encoding = "gzip"
    else:
        decoded = raw
        encoding = "plain"
    if not decoded:
        raise GateInputError("decoded replay is empty")
    if len(decoded) > MAX_REPLAY_BYTES:
        raise GateInputError(
            f"decoded replay exceeds {MAX_REPLAY_BYTES} byte ceiling"
        )
    return raw, decoded, encoding


def _load_replay(decoded: bytes) -> Mapping[str, Any]:
    try:
        text = decoded.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GateInputError(f"replay is not UTF-8 JSON: {exc}") from exc

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise GateInputError(f"duplicate JSON key is ambiguous: {key!r}")
            result[key] = value
        return result

    def reject_nonfinite(token: str) -> None:
        raise GateInputError(f"non-finite JSON number is invalid: {token}")

    try:
        value = json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonfinite,
        )
    except json.JSONDecodeError as exc:
        raise GateInputError(f"replay is not valid JSON: {exc}") from exc
    return _require_mapping(value, "replay")


def _agent_name(info: Mapping[str, Any], seat: int) -> str:
    agents = _require_list(_require_key(info, "Agents", "replay.info"), "replay.info.Agents")
    if seat >= len(agents):
        raise GateInputError(
            f"seat {seat} is outside replay.info.Agents length {len(agents)}"
        )
    agent = _require_mapping(agents[seat], f"replay.info.Agents[{seat}]")
    return _exact_string(
        _require_key(agent, "Name", f"replay.info.Agents[{seat}]"),
        f"replay.info.Agents[{seat}].Name",
    )


def _observation_for_record(record: Any, *, step: int, seat: int) -> Mapping[str, Any]:
    rec = _require_mapping(record, f"steps[{step}][{seat}]")
    observation = _require_mapping(
        _require_key(rec, "observation", f"steps[{step}][{seat}]"),
        f"steps[{step}][{seat}].observation",
    )
    player = _exact_int(
        _require_key(observation, "player", f"steps[{step}][{seat}].observation"),
        f"steps[{step}][{seat}].observation.player",
        minimum=0,
    )
    if player != seat:
        raise GateInputError(
            f"steps[{step}][{seat}].observation.player={player}, expected seat {seat}"
        )
    return observation


def _observable_hand_count(observation: Mapping[str, Any], *, step: int, seat: int) -> int:
    farms = _require_list(
        _require_key(observation, "farms", f"steps[{step}][{seat}].observation"),
        f"steps[{step}][{seat}].observation.farms",
    )
    if seat >= len(farms):
        raise GateInputError(
            f"steps[{step}][{seat}].observation.farms has no own farm at index {seat}"
        )
    farm = _require_mapping(farms[seat], f"steps[{step}][{seat}].observation.farms[{seat}]")
    hands = _require_list(
        _require_key(
            farm,
            "hands",
            f"steps[{step}][{seat}].observation.farms[{seat}]",
        ),
        f"steps[{step}][{seat}].observation.farms[{seat}].hands",
    )
    return len(hands)


def _day_hour(observation: Mapping[str, Any], *, label: str) -> tuple[int, int]:
    day = _exact_int(_require_key(observation, "day", label), f"{label}.day", minimum=0)
    hour = _exact_int(_require_key(observation, "hour", label), f"{label}.hour", minimum=0)
    return day, hour


def _action_for_record(record: Any, *, step: int, seat: int) -> Mapping[str, Any]:
    rec = _require_mapping(record, f"steps[{step}][{seat}]")
    return _require_mapping(
        _require_key(rec, "action", f"steps[{step}][{seat}]"),
        f"steps[{step}][{seat}].action",
    )


def _violation_ranges(violations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for violation in violations:
        if (
            groups
            and violation["step"] == groups[-1]["end_step"] + 1
            and violation["observable_hands"] == groups[-1]["observable_hands"]
            and violation["submitted_hand_rows"] == groups[-1]["submitted_hand_rows"]
        ):
            group = groups[-1]
            group["end_step"] = violation["step"]
            group["end_day"] = violation["day"]
            group["end_hour"] = violation["hour"]
            group["count"] += 1
        else:
            groups.append(
                {
                    "start_step": violation["step"],
                    "end_step": violation["step"],
                    "count": 1,
                    "observable_hands": violation["observable_hands"],
                    "submitted_hand_rows": violation["submitted_hand_rows"],
                    "start_day": violation["day"],
                    "start_hour": violation["hour"],
                    "end_day": violation["day"],
                    "end_hour": violation["hour"],
                }
            )
    return groups


