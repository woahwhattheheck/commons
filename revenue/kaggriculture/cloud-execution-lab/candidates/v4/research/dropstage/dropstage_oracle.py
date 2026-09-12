#!/usr/bin/env python3
"""Fail-closed proof helpers for TITAN V4 DROPSTAGE.

DROPSTAGE does not authorize runtime mutation. It proves one conservative
replacement primitive: on the final callback of a day, replace a lossy single-item
manual DROP with an equivalent bounded PLACE only when a caller proves enough
post-market shed room to return every preserved unit without crowding any other
end-of-day carry.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from typing import Mapping, Any

ENGINE_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
TAPE_BLOB = "a43289b9cc5e34a2481fddf652762a7d92f427ef"
STATE = "THEOREM_PROVEN_NATURAL_REPLAY_REQUIRED"


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def authenticate_sources(cloud_root: Path) -> dict[str, str]:
    engine = cloud_root / "reference" / "engine" / "kaggriculture.py"
    tapes = cloud_root / "candidates" / "v4" / "donor" / "overlay" / "r01_tapes.py"
    receipt = {"engine_blob": git_blob(engine), "tape_blob": git_blob(tapes)}
    expected = {"engine_blob": ENGINE_BLOB, "tape_blob": TAPE_BLOB}
    if receipt != expected:
        raise RuntimeError(f"DROPSTAGE source drift: {receipt}")
    return receipt


def load_tapes(tape_path: Path) -> list[list[dict[str, Any]]]:
    spec = importlib.util.spec_from_file_location("_dropstage_tapes", tape_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    tapes = module.load_tapes()
    if len(tapes) != 13 or any(len(tape) != 719 for tape in tapes):
        raise RuntimeError("DROPSTAGE expected exact 13x719 donor tapes")
    return tapes


def unit_actions(action: Mapping[str, Any]):
    farmer = action.get("farmer", ["PASS"])
    hands = action.get("hands", [])
    yield "farmer", farmer
    if isinstance(hands, list):
        for index, row in enumerate(hands):
            yield f"hand:{index}", row


def donor_drop_census(tapes: list[list[dict[str, Any]]]) -> dict[str, Any]:
    """Inventory authored DROP syntax only; dynamic loss requires exact replay."""
    sites: list[dict[str, Any]] = []
    place_sites = 0
    for tape_id, tape in enumerate(tapes):
        for step, action in enumerate(tape):
            for actor_slot, row in unit_actions(action):
                if not isinstance(row, list) or not row:
                    continue
                op = row[0]
                if op == "DROP":
                    sites.append({"tape": tape_id, "step": step, "actor_slot": actor_slot, "action": row})
                elif op == "PLACE":
                    place_sites += 1
    return {
        "drop_sites": sites,
        "drop_site_count": len(sites),
        "place_site_count": place_sites,
        "disposition": "COLD_NO_AUTHORED_DROP" if not sites else "REPLAY_REQUIRED",
    }


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _positive_carry(carried_inputs: Mapping[str, Any]) -> list[tuple[str, int]] | None:
    if not isinstance(carried_inputs, Mapping):
        return None
    positive: list[tuple[str, int]] = []
    for item, qty in carried_inputs.items():
        if not isinstance(item, str) or not item or not _nonnegative_int(qty):
            return None
        if qty:
            positive.append((item, qty))
    return positive


def manual_drop_outcome(carry_qty: int, shed_free_before_units: int) -> dict[str, int]:
    if not (_nonnegative_int(carry_qty) and _nonnegative_int(shed_free_before_units)):
        raise ValueError("quantities must be non-negative integers")
    deposited = min(carry_qty, shed_free_before_units)
    return {"deposited_before_market": deposited, "carried_after_units": 0, "destroyed_before_market": carry_qty - deposited}


def staged_place_outcome(
    carry_qty: int,
    shed_free_before_units: int,
    eod_room_after_market: int,
) -> dict[str, int]:
    if not all(_nonnegative_int(v) for v in (carry_qty, shed_free_before_units, eod_room_after_market)):
        raise ValueError("quantities must be non-negative integers")
    deposited = min(carry_qty, shed_free_before_units)
    preserved = carry_qty - deposited
    returned = min(preserved, eod_room_after_market)
    return {
        "deposited_before_market": deposited,
        "carried_into_market": preserved,
        "returned_at_eod": returned,
        "destroyed_at_eod": preserved - returned,
    }


def proof_receipt(carry_qty: int, shed_free_before_units: int, eod_room_after_market: int) -> dict[str, Any]:
    drop = manual_drop_outcome(carry_qty, shed_free_before_units)
    place = staged_place_outcome(carry_qty, shed_free_before_units, eod_room_after_market)
    return {
        "drop": drop,
        "place": place,
        "saved_units": drop["destroyed_before_market"] - place["destroyed_at_eod"],
        "market_start_shed_delta": 0,
    }


def admit_dropstage(
    *,
    carried_inputs: Mapping[str, Any],
    shed_free_before_units: Any,
    eod_room_after_market_lower_bound: Any,
    other_eod_carry_units: Any,
    is_final_callback_of_day: bool,
    place_supported: bool,
) -> list[Any] | None:
    """Return a semantics-safe PLACE replacement, otherwise fail closed.

    The lower bound must describe room *after the complete market phase*. Requiring
    it to fit the staged remainder plus all other EOD carry prevents DROPSTAGE from
    merely moving loss onto another actor. The transform deliberately requires a
    single positive carried item so pre-market shed state is identical to DROP.
    """
    positive = _positive_carry(carried_inputs)
    if positive is None or len(positive) != 1:
        return None
    if not (_nonnegative_int(shed_free_before_units)
            and _nonnegative_int(eod_room_after_market_lower_bound)
            and _nonnegative_int(other_eod_carry_units)):
        return None
    if is_final_callback_of_day is not True or place_supported is not True:
        return None

    item, qty = positive[0]
    if qty <= shed_free_before_units:
        return None

    remainder = qty - shed_free_before_units
    required_room = remainder + other_eod_carry_units
    if eod_room_after_market_lower_bound < required_room:
        return None

    return ["PLACE", item, qty]
