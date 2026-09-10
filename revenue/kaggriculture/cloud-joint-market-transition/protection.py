# SPDX-License-Identifier: Apache-2.0
"""Internal support for the exact TITAN joint transition oracle."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from engine_binding import _copy, canonical_sha256


def _decode_pointer_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _json_pointer(value: Any, pointer: str) -> Any:
    if pointer == "":
        return value
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError(f"invalid_json_pointer:{pointer!r}")
    current = value
    for raw in pointer[1:].split("/"):
        token = _decode_pointer_token(raw)
        if isinstance(current, list):
            if not token.isdigit():
                raise ValueError(f"non_numeric_list_pointer:{pointer}")
            index = int(token)
            if index >= len(current):
                raise ValueError(f"list_pointer_out_of_range:{pointer}")
            current = current[index]
        elif isinstance(current, dict):
            if token not in current:
                raise ValueError(f"missing_pointer:{pointer}")
            current = current[token]
        else:
            raise ValueError(f"pointer_through_scalar:{pointer}")
    return current


def _stage(arm: Mapping[str, Any], stage: Any) -> Any:
    if stage == "initial":
        return arm["prefixes"][0]
    if stage == "pre_town":
        return {"state": arm["pre_town_state"], "state_hash": arm["pre_town_state_hash"]}
    if stage == "post_town":
        return {"state": arm["post_town_state"], "state_hash": arm["post_town_state_hash"], "town_effect": arm["town_effect"]}
    if type(stage) is int and 0 <= stage < len(arm["prefixes"]):
        return arm["prefixes"][stage]
    raise ValueError(f"invalid_checkpoint_stage:{stage!r}")


def _evaluate_checkpoints(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    checkpoints: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    names: set[str] = set()
    for checkpoint in checkpoints:
        if not isinstance(checkpoint, dict):
            raise ValueError("checkpoint_must_be_dict")
        name = checkpoint.get("name")
        if not isinstance(name, str) or not name or name in names:
            raise ValueError("checkpoint_names_must_be_unique_nonempty_strings")
        names.add(name)
        paths = checkpoint.get("paths")
        if not isinstance(paths, list) or not paths or not all(isinstance(path, str) for path in paths):
            raise ValueError(f"checkpoint_paths_required:{name}")
        baseline_stage = _stage(baseline, checkpoint.get("baseline_stage"))
        candidate_stage = _stage(candidate, checkpoint.get("candidate_stage"))
        comparisons = []
        for path in paths:
            before = _copy(_json_pointer(baseline_stage, path))
            after = _copy(_json_pointer(candidate_stage, path))
            comparisons.append({
                "path": path,
                "equal": before == after,
                "baseline": before,
                "candidate": after,
                "baseline_hash": canonical_sha256(before),
                "candidate_hash": canonical_sha256(after),
            })
        results.append({
            "name": name,
            "baseline_stage": checkpoint.get("baseline_stage"),
            "candidate_stage": checkpoint.get("candidate_stage"),
            "passed": all(row["equal"] for row in comparisons),
            "comparisons": comparisons,
        })
    return {
        "requested": bool(results),
        "status": "PASS" if results and all(row["passed"] for row in results) else "HOLD" if results else "UNSPECIFIED",
        "checkpoints": results,
    }


def _comparison(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    seat: int,
    checkpoints: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    own = seat
    rival = 1 - seat
    own_cash = candidate["post_town_state"]["farms"][own]["money"] - baseline["post_town_state"]["farms"][own]["money"]
    rival_cash = candidate["post_town_state"]["farms"][rival]["money"] - baseline["post_town_state"]["farms"][rival]["money"]
    inherited_changes = []
    count = max(len(baseline["prefixes"]), len(candidate["prefixes"]))
    for prefix_length in range(1, count):
        b = baseline["prefixes"][prefix_length] if prefix_length < len(baseline["prefixes"]) else None
        c = candidate["prefixes"][prefix_length] if prefix_length < len(candidate["prefixes"]) else None
        if b is None or c is None:
            continue
        for player in (0, 1):
            if b["orders"][player] is not None and b["orders"][player] == c["orders"][player]:
                if b["executions"][player] != c["executions"][player]:
                    inherited_changes.append({
                        "prefix_length": prefix_length,
                        "player": player,
                        "order": _copy(b["orders"][player]),
                        "baseline": _copy(b["executions"][player]),
                        "candidate": _copy(c["executions"][player]),
                    })
    return {
        "own_cash_delta": own_cash,
        "rival_cash_delta": rival_cash,
        "relative_cash_delta": own_cash - rival_cash,
        "pre_town_state_equal": baseline["pre_town_state_hash"] == candidate["pre_town_state_hash"],
        "post_town_state_equal": baseline["post_town_state_hash"] == candidate["post_town_state_hash"],
        "inherited_same_slot_execution_changes": inherited_changes,
        "protection": _evaluate_checkpoints(baseline, candidate, checkpoints),
    }
