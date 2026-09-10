# SPDX-License-Identifier: Apache-2.0
"""Strict state and queue guards for the stranded-HIRE payback certificate."""
from __future__ import annotations
import copy
import hashlib
import json
from typing import Any, Mapping
import mechanics as m

SCHEMA_VERSION = 1

_ALLOWED_NEW_HAND_OPS = frozenset(
    {
        "PASS",
        "NORTH",
        "SOUTH",
        "EAST",
        "WEST",
        "HARVEST",
        "DROP",
        "COLLECT_FERTILIZER",
    }
)

_ONE_TOKEN_OPS = _ALLOWED_NEW_HAND_OPS

class _Reject(ValueError):
    """Internal fail-closed boundary with a stable machine reason."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(detail or reason)
        self.reason = reason
        self.detail = detail

def _strict_int(value: Any, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _Reject("invalid_integer", f"{name} must be a non-bool integer")
    if minimum is not None and value < minimum:
        raise _Reject("invalid_integer", f"{name} must be >= {minimum}")
    return value

def _json_clone(value: Any, name: str) -> Any:
    try:
        encoded = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return json.loads(encoded)
    except (TypeError, ValueError, OverflowError) as exc:
        raise _Reject("non_json_input", f"{name}: {type(exc).__name__}: {exc}") from exc

def _digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()

def _idle_row(row: Any) -> bool:
    return row == [] or (
        isinstance(row, list)
        and len(row) == 3
        and row[0] == "SELL"
        and isinstance(row[2], int)
        and not isinstance(row[2], bool)
        and row[2] == 0
    )

def _verify_single_hire_delta(
    baseline: list[Any], candidate: list[Any], inserted_index: int
) -> None:
    if inserted_index < 0:
        raise _Reject("invalid_inserted_index")
    if inserted_index == len(baseline):
        if candidate != [*baseline, ["HIRE"]]:
            raise _Reject("market_delta_not_single_append")
        return
    if inserted_index >= len(baseline) or len(candidate) != len(baseline):
        raise _Reject("market_delta_shape_mismatch")
    if not _idle_row(baseline[inserted_index]):
        raise _Reject("replaced_row_not_inert")
    for index, (before, after) in enumerate(zip(baseline, candidate)):
        expected = ["HIRE"] if index == inserted_index else before
        if after != expected:
            raise _Reject("market_delta_not_single_replacement", f"index={index}")

def _validate_state(farm: Any, private: Any, cfg: Mapping[str, Any]) -> tuple[dict, dict, int]:
    if not isinstance(farm, Mapping) or not isinstance(private, Mapping):
        raise _Reject("invalid_state_shape")
    farm_copy = _json_clone(dict(farm), "farm")
    private_copy = _json_clone(dict(private), "private")

    tiles = farm_copy.get("tiles")
    hands = farm_copy.get("hands")
    inventories = private_copy.get("inventories")
    shed = private_copy.get("shed")
    if not isinstance(tiles, list) or not tiles or not all(isinstance(row, list) for row in tiles):
        raise _Reject("invalid_tiles")
    board_size = len(tiles)
    if any(len(row) != board_size for row in tiles):
        raise _Reject("non_square_tiles")
    configured_board = cfg.get("boardSize", board_size)
    if _strict_int(configured_board, "boardSize", minimum=1) != board_size:
        raise _Reject("board_size_mismatch")
    if not isinstance(hands, list) or not isinstance(inventories, list):
        raise _Reject("invalid_actor_state")
    if len(inventories) != len(hands) + 1:
        raise _Reject("inventory_actor_mismatch")
    if not isinstance(shed, dict):
        raise _Reject("invalid_shed")
    for product in m.PRODUCTS:
        quantity = shed.get(product, 0)
        _strict_int(quantity, f"shed.{product}", minimum=0)
    return farm_copy, private_copy, board_size
