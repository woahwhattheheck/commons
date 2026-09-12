# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import tempfile
import unittest

import promotion_closure as pc


def d(label: str) -> str:
    import hashlib

    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def step_series(label: str) -> list[dict[str, object]]:
    return [
        {
            "step": index,
            "preworld_sha256": d(f"{label}:pre:{index}"),
            "observation_sha256": d(f"{label}:obs:{index}"),
            "tested_action_sha256": d(f"{label}:tested:{index}"),
            "rival_action_sha256": d(f"{label}:rival:{index}"),
            "postworld_sha256": d(f"{label}:post:{index}"),
            "bank_sha256": d(f"{label}:bank:{index}"),
        }
        for index in range(pc.EXPECTED_STEPS)
    ]


def arm(
    label: str,
    *,
    own: float,
    rival: float,
    base_steps: list[dict[str, object]] | None = None,
    changed: bool = False,
    replay: bool = True,
) -> dict[str, object]:
    steps = copy.deepcopy(base_steps if base_steps is not None else step_series(label))
    if changed:
        steps[3]["tested_action_sha256"] = d(f"{label}:changed-action")
        steps[3]["postworld_sha256"] = d(f"{label}:changed-world")
        steps[3]["bank_sha256"] = d(f"{label}:changed-bank")
        # A causally divergent postworld becomes the next preworld.
        steps[4]["preworld_sha256"] = steps[3]["postworld_sha256"]
        steps[4]["observation_sha256"] = d(f"{label}:changed-obs-4")
    terminal = {"own_cash": own, "rival_cash": rival}
    trace = pc.json_sha256({"steps": steps, "terminal": terminal})
    result: dict[str, object] = {
        "invocation_id": f"{label}:primary",
        "trace_sha256": trace,
        "steps": steps,
        "terminal": terminal,
        "replay": None,
    }
    if replay:
        result["replay"] = {
            "invocation_id": f"{label}:replay",
            "trace_sha256": trace,
            "own_cash": own,
            "rival_cash": rival,
        }
    return result


def cell(opponent: str, seed: int, seat: int, *, own_delta: float = 2.0) -> dict[str, object]:
    common = step_series(f"{opponent}:{seed}:{seat}")
    control = arm(
        f"control:{opponent}:{seed}:{seat}",
        own=100.0,
        rival=90.0,
        base_steps=common,
        changed=False,
    )
    candidate = arm(
        f"candidate:{opponent}:{seed}:{seat}",
        own=100.0 + own_delta,
        rival=90.0,
        base_steps=common,
        changed=True,
    )
    return {
        "opponent": opponent,
        "seed": seed,
        "candidate_seat": seat,
        "paired_verdict": "ACTION_CHANGE",
        "control": control,
        "candidate": candidate,
    }


def policy() -> dict[str, object]:
    return {
        "schema_version": pc.POLICY_SCHEMA,
        "min_global_mean_own_delta": 0.01,
        "min_global_mean_margin_delta": 0.01,
        "min_opponent_seat_mean_own_delta": 0.0,
        "min_opponent_seat_mean_margin_delta": 0.0,
        "min_cell_own_delta": -5.0,
        "min_cell_margin_delta": -5.0,
        "lower_quantile": 0.10,
        "min_lower_quantile_own_delta": 0.0,
        "min_lower_quantile_margin_delta": 0.0,
        "min_seed_mean_own_delta": 0.0,
        "min_seed_mean_margin_delta": 0.0,
        "min_positive_seed_clusters": 5,
        "max_negative_seed_clusters": 0,
        "max_seed_sign_tail": 0.05,
        "require_zero_new_losses": True,
        "require_zero_lost_wins": True,
        "require_zero_outcome_regressions": True,
    }




def closure(label: str) -> dict[str, object]:
    payload = label.encode("utf-8")
    import hashlib

    member = {
        "path": "main.py",
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "git_blob_sha1": hashlib.sha1(
            b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        ).hexdigest(),
    }
    base: dict[str, object] = {
        "schema_version": pc.CLOSURE_SCHEMA,
        "entry": "main.py",
        "members": [member],
        "modules": {"main": {"path": "main.py", "sha256": member["sha256"]}},
    }
    return {**base, "closure_sha256": pc.json_sha256(base)}


def spent_ledger() -> dict[str, object]:
    return {
        "schema_version": pc.LEDGER_SCHEMA,
        "entries": [
            {
                "operation": "titan-v3-own-value-disjoint-holdout-sol-pro-20260910-01",
                "hypothesis": "own-value-score0",
                "head": "b1962a216fafd1c654fb96b2a4baa5fb81e2f1c0",
                "source_pr": 12040,
                "run_id": 34524185925,
                "run_attempt": 1,
                "event_name": "pull_request",
                "policy_sha256": "679f1ab5a83369696a9b28e4647cb9aae38b0a2b60afb91d3a993238a66a908d",
                "seeds": [
                    1201189346,
                    2053792019,
                    684357706,
                    572159600,
                    1619590821,
                    1748784700,
                    2100322278,
                    1851971276,
                ],
                "status": "spent",
                "reuse_forbidden": True,
            }
        ],
    }


def panel(*, seeds: list[int] | None = None, opponents: list[str] | None = None) -> dict[str, object]:
    seeds = seeds or [11, 12, 13, 14, 15]
    opponents = opponents or ["apex"]
    p = policy()
    cells = [
        cell(opponent, seed, seat)
        for opponent in opponents
        for seed in seeds
        for seat in (0, 1)
    ]
    run = {
        "operation": "titan-v3-own-value-promotion-holdout-sol-pro-20260910-02",
        "hypothesis": "own-value-score0",
        "head": "1" * 40,
        "source_pr": 12099,
        "run_id": 9990001,
        "run_attempt": 1,
        "event_name": "pull_request",
        "policy_sha256": pc.json_sha256(pc.validate_policy(p)),
        "seeds": list(seeds),
        "status": "spent",
        "reuse_forbidden": True,
    }
    return {
        "schema_version": pc.TRAJECTORY_SCHEMA,
        "operation": run["operation"],
        "hypothesis": run["hypothesis"],
        "head": run["head"],
        "policy_sha256": run["policy_sha256"],
        "engine_sha256": d("engine"),
        "evaluator_sha256": d("evaluator"),
        "loader_sha256": d("loader"),
        "seeds": list(seeds),
        "opponents": {name: closure(f"opponent:{name}") for name in opponents},
        "closures": {
            "control": closure("control-root"),
            "candidate": closure("candidate-root"),
        },
        "run": run,
        "cells": cells,
    }


def refresh_arm_trace(arm_value: dict[str, object]) -> None:
    arm_value["trace_sha256"] = pc.json_sha256(
        {"steps": arm_value["steps"], "terminal": arm_value["terminal"]}
    )
    replay = arm_value.get("replay")
    if isinstance(replay, dict):
        replay["trace_sha256"] = arm_value["trace_sha256"]
        replay["own_cash"] = arm_value["terminal"]["own_cash"]
        replay["rival_cash"] = arm_value["terminal"]["rival_cash"]


