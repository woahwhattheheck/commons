#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Native paired-trajectory custody for TITAN promotion evidence."""
from __future__ import annotations

from promotion_core import *
from promotion_seed import *
from promotion_manifest import *

STEP_KEYS = {
    "step",
    "preworld_sha256",
    "observation_sha256",
    "tested_action_sha256",
    "rival_action_sha256",
    "postworld_sha256",
    "bank_sha256",
}
ARM_KEYS = {"invocation_id", "trace_sha256", "steps", "terminal", "replay"}
REPLAY_KEYS = {"invocation_id", "trace_sha256", "own_cash", "rival_cash"}
CELL_KEYS = {"opponent", "seed", "candidate_seat", "paired_verdict", "control", "candidate"}
PANEL_KEYS = {
    "schema_version",
    "operation",
    "hypothesis",
    "head",
    "policy_sha256",
    "engine_sha256",
    "evaluator_sha256",
    "loader_sha256",
    "seeds",
    "opponents",
    "closures",
    "run",
    "cells",
}


def _validated_step(raw: Mapping[str, Any], index: int, label: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise PromotionClosureError(f"{label} step {index} must be an object")
    require_keys(raw, STEP_KEYS, f"{label} step {index}")
    if true_int(raw["step"], f"{label}.step", minimum=0) != index:
        raise PromotionClosureError(f"{label} step sequence is not contiguous")
    return {
        "step": index,
        "preworld_sha256": sha64(raw["preworld_sha256"], f"{label} preworld"),
        "observation_sha256": sha64(raw["observation_sha256"], f"{label} observation"),
        "tested_action_sha256": sha64(raw["tested_action_sha256"], f"{label} tested action"),
        "rival_action_sha256": sha64(raw["rival_action_sha256"], f"{label} rival action"),
        "postworld_sha256": sha64(raw["postworld_sha256"], f"{label} postworld"),
        "bank_sha256": sha64(raw["bank_sha256"], f"{label} bank"),
    }


def _validated_arm(raw: Mapping[str, Any], label: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise PromotionClosureError(f"{label} arm must be an object")
    require_keys(raw, ARM_KEYS, f"{label} arm")
    invocation = nonempty_string(raw["invocation_id"], f"{label}.invocation_id")
    steps_raw = raw["steps"]
    if not isinstance(steps_raw, list) or len(steps_raw) != EXPECTED_STEPS:
        raise PromotionClosureError(
            f"{label} must retain exactly {EXPECTED_STEPS} trajectory steps"
        )
    steps = [_validated_step(step, index, label) for index, step in enumerate(steps_raw)]
    terminal_raw = raw["terminal"]
    if not isinstance(terminal_raw, Mapping):
        raise PromotionClosureError(f"{label}.terminal must be an object")
    require_keys(terminal_raw, {"own_cash", "rival_cash"}, f"{label}.terminal")
    terminal = {
        "own_cash": finite(terminal_raw["own_cash"], f"{label} own cash"),
        "rival_cash": finite(terminal_raw["rival_cash"], f"{label} rival cash"),
    }
    computed_trace = json_sha256({"steps": steps, "terminal": terminal})
    supplied_trace = sha64(raw["trace_sha256"], f"{label}.trace_sha256")
    if supplied_trace != computed_trace:
        raise PromotionClosureError(f"{label} trace digest is detached")

    replay_raw = raw["replay"]
    replay: dict[str, Any] | None
    if replay_raw is None:
        replay = None
    else:
        if not isinstance(replay_raw, Mapping):
            raise PromotionClosureError(f"{label}.replay must be null or an object")
        require_keys(replay_raw, REPLAY_KEYS, f"{label}.replay")
        replay = {
            "invocation_id": nonempty_string(
                replay_raw["invocation_id"], f"{label}.replay.invocation_id"
            ),
            "trace_sha256": sha64(
                replay_raw["trace_sha256"], f"{label}.replay.trace_sha256"
            ),
            "own_cash": finite(replay_raw["own_cash"], f"{label}.replay.own_cash"),
            "rival_cash": finite(
                replay_raw["rival_cash"], f"{label}.replay.rival_cash"
            ),
        }
        if replay["invocation_id"] == invocation:
            raise PromotionClosureError(f"{label} replay is not an independent invocation")
    return {
        "invocation_id": invocation,
        "trace_sha256": supplied_trace,
        "steps": steps,
        "terminal": terminal,
        "replay": replay,
    }


def _require_replay(arm: Mapping[str, Any], label: str) -> None:
    replay = arm["replay"]
    if replay is None:
        raise PromotionClosureError(f"score-active {label} lacks deterministic replay")
    if replay["trace_sha256"] != arm["trace_sha256"]:
        raise PromotionClosureError(f"score-active {label} replay trace differs")
    if replay["own_cash"] != arm["terminal"]["own_cash"]:
        raise PromotionClosureError(f"score-active {label} replay own cash differs")
    if replay["rival_cash"] != arm["terminal"]["rival_cash"]:
        raise PromotionClosureError(f"score-active {label} replay rival cash differs")


def _outcome(own: float, rival: float) -> str:
    if own > rival:
        return "win"
    if own < rival:
        return "loss"
    return "tie"


def compare_cell(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise PromotionClosureError("panel cell must be an object")
    require_keys(raw, CELL_KEYS, "panel cell")
    opponent = nonempty_string(raw["opponent"], "cell opponent")
    seed = true_int(raw["seed"], "cell seed", minimum=0)
    seat = true_int(raw["candidate_seat"], "cell candidate seat", minimum=0)
    if seat not in (0, 1):
        raise PromotionClosureError("candidate seat must be 0 or 1")
    paired_verdict = nonempty_string(raw["paired_verdict"], "paired verdict")
    if paired_verdict not in {"ACTION_CHANGE", "NO_ACTION_CHANGE"}:
        raise PromotionClosureError("unknown paired verdict")
    control = _validated_arm(raw["control"], "control")
    candidate = _validated_arm(raw["candidate"], "candidate")
    if control["invocation_id"] == candidate["invocation_id"]:
        raise PromotionClosureError("control and candidate invocations are not distinct")

    first_divergence: int | None = None
    realized = False
    for index, (left, right) in enumerate(zip(control["steps"], candidate["steps"])):
        if first_divergence is None and left["tested_action_sha256"] != right["tested_action_sha256"]:
            first_divergence = index
            for field in ("preworld_sha256", "observation_sha256", "rival_action_sha256"):
                if left[field] != right[field]:
                    raise PromotionClosureError(
                        f"first tested-action divergence is confounded at {field}"
                    )
            realized = left["postworld_sha256"] != right["postworld_sha256"]
            if not realized:
                raise PromotionClosureError(
                    "first tested-action divergence did not change the realized postworld"
                )
        elif first_divergence is None and left != right:
            raise PromotionClosureError(
                "world, observation, rival action, or bank diverged before tested action"
            )

    own_delta = candidate["terminal"]["own_cash"] - control["terminal"]["own_cash"]
    rival_delta = candidate["terminal"]["rival_cash"] - control["terminal"]["rival_cash"]
    margin_delta = own_delta - rival_delta
    score_changed = own_delta != 0 or rival_delta != 0
    trace_changed = control["trace_sha256"] != candidate["trace_sha256"]
    action_changed = first_divergence is not None

    if paired_verdict == "NO_ACTION_CHANGE" and (action_changed or score_changed):
        raise PromotionClosureError("NO_ACTION_CHANGE cannot coexist with changed evidence")
    if paired_verdict == "ACTION_CHANGE" and not action_changed:
        raise PromotionClosureError("ACTION_CHANGE lacks a tested-action divergence")
    if score_changed and not trace_changed:
        raise PromotionClosureError("score changed while complete trajectory trace stayed identical")
    if score_changed and not action_changed:
        raise PromotionClosureError("score changed without tested-action divergence")
    if score_changed:
        _require_replay(control, "control")
        _require_replay(candidate, "candidate")

    before = _outcome(control["terminal"]["own_cash"], control["terminal"]["rival_cash"])
    after = _outcome(candidate["terminal"]["own_cash"], candidate["terminal"]["rival_cash"])
    return {
        "opponent": opponent,
        "seed": seed,
        "candidate_seat": seat,
        "first_tested_action_divergence": first_divergence,
        "realized_first_divergence": realized,
        "action_changed": action_changed,
        "trace_changed": trace_changed,
        "score_changed": score_changed,
        "control_own_cash": control["terminal"]["own_cash"],
        "candidate_own_cash": candidate["terminal"]["own_cash"],
        "own_cash_delta": own_delta,
        "control_rival_cash": control["terminal"]["rival_cash"],
        "candidate_rival_cash": candidate["terminal"]["rival_cash"],
        "rival_cash_delta": rival_delta,
        "margin_delta": margin_delta,
        "control_outcome": before,
        "candidate_outcome": after,
        "new_loss": before != "loss" and after == "loss",
        "lost_win": before == "win" and after != "win",
        "outcome_regression": OUTCOME_RANK[after] < OUTCOME_RANK[before],
    }


