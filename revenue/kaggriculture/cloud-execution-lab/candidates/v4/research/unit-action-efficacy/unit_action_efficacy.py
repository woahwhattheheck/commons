# SPDX-License-Identifier: Apache-2.0
"""Source-bound unit-action efficacy tracer for the TITAN V4 b567 native fixture.

This is an evidence tool.  It never edits actions, runtime source, defaults, or
package bytes.  One process traces one seed/seat so agent globals cannot leak
between cells.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import sys
from collections import Counter
from pathlib import Path

ENGINE_REL = Path("checks/reference/engine/kaggriculture.py")
MAIN_REL = Path("main.py")
ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
MAIN_GIT_BLOB = "4a8cf7bcda1f0fea231a144692cb84a779a9e73e"
ARTIFACT_ID = 10175943272
INNER_TAR_SHA256 = "b567942e4fb4e0571ebf9f8eaaf143d4a9156df3289f09a98db37823ef4d68d9"

ONE_SHOT_TILE_OPS = frozenset({"CARE", "WATER", "COLLECT_FERTILIZER", "HARVEST"})


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _verify(path: Path, expected: str, label: str) -> None:
    actual = git_blob_sha(path.read_bytes())
    if actual != expected:
        raise ValueError(f"{label} Git blob mismatch: expected {expected}, got {actual}")


def effect_target(position, action):
    """Return a conservative semantic target used only for attribution.

    The four one-shot tile operations are intentionally narrow: a later no-op
    is attributed to a predecessor only when the earlier actor succeeded on the
    same tile with the same operation.  Other no-ops remain unclassified.
    """
    if not isinstance(action, list) or not action:
        return None
    op = action[0]
    if op in ONE_SHOT_TILE_OPS:
        return ("tile", tuple(position), op)
    return None


def trace_unit_vector(engine, farm, private, action, *, step: int, cfg: dict):
    """Replay only the official unit phase on private copies and report effects."""
    farm = copy.deepcopy(farm)
    private = copy.deepcopy(private)
    farmer_action = action.get("farmer", ["PASS"]) if isinstance(action, dict) else ["PASS"]
    hands_actions = action.get("hands", []) if isinstance(action, dict) else []
    if not isinstance(hands_actions, list):
        hands_actions = []
    unit_actions = [farmer_action, *hands_actions]

    plant_demand = Counter()
    for cmd in unit_actions:
        if isinstance(cmd, list) and len(cmd) >= 2 and cmd[0] == "PLANT":
            plant_demand[cmd[1]] += 1
    seeds = private.get("seeds", {}) if isinstance(private, dict) else {}
    blocked = {crop for crop, n in plant_demand.items() if n > seeds.get(crop, 0)}

    positions = [tuple(farm["farmer"]), *[tuple(p) for p in farm["hands"]]]
    board_size = int(cfg.get("boardSize", 10))
    turns_per_day = max(1, int(cfg.get("turnsPerDay", 24)))
    shed_capacity = int(cfg.get("shedCapacity", 100))
    day = int(step) // turns_per_day

    successful_targets = {}
    rows = []
    for idx, raw in enumerate(unit_actions):
        if idx >= len(positions):
            break
        blocked_plant = (
            isinstance(raw, list) and len(raw) >= 2 and raw[0] == "PLANT" and raw[1] in blocked
        )
        cmd = ["PASS"] if blocked_plant else raw
        op = cmd[0] if isinstance(cmd, list) and cmd else "<MALFORMED>"
        before_farm, before_private = copy.deepcopy(farm), copy.deepcopy(private)
        engine._apply_unit_action(
            farm, private, idx, cmd, board_size, day, turns_per_day, shed_capacity
        )
        changed = farm != before_farm or private != before_private
        target = effect_target(positions[idx], cmd)
        predecessor = successful_targets.get(target) if target is not None and not changed else None
        if target is not None and changed:
            successful_targets.setdefault(target, idx)
        rows.append({
            "actor_index": idx,
            "position": list(positions[idx]),
            "raw_action": raw,
            "effective_action": cmd,
            "op": op,
            "changed": bool(changed),
            "atomic_plant_blocked": bool(blocked_plant),
            "same_target_successful_predecessor": predecessor,
        })
    return rows


def _load_fixture(package: Path):
    _verify(package / ENGINE_REL, ENGINE_GIT_BLOB, "official engine")
    _verify(package / MAIN_REL, MAIN_GIT_BLOB, "native main.py")
    sys.path.insert(0, str(package))
    sys.path.insert(1, str(package / "checks"))
    from test_engine_semantics import EngineSemantics
    EngineSemantics.setUpClass()
    engine, ev = EngineSemantics.engine, EngineSemantics.ev
    main = importlib.import_module("main")
    return engine, ev, main


def run_cell(package: Path, seed: int, seat: int):
    if seat not in (0, 1):
        raise ValueError("seat must be 0 or 1")
    engine, ev, main = _load_fixture(package)
    cfg = ev.Struct({
        k: (v.get("default") if isinstance(v, dict) else v)
        for k, v in engine.specification["configuration"].items()
    })
    cfg.seed = int(seed)
    env = ev.Struct(configuration=cfg, done=False, info={})
    state = [
        ev.Struct(observation=ev.Struct(), action={}, status="ACTIVE", reward=0)
        for _ in range(2)
    ]
    engine.interpreter(state, env)

    by_op = {}
    same_target = []
    callbacks = 0
    nonpass = 0
    for step in range(int(cfg.episodeSteps)):
        actions = []
        for player in range(2):
            state[player].observation.step = step
            state[player].observation.remainingOverageTime = 0
            if player == seat:
                obs = state[player].observation
                act = main.agent(copy.deepcopy(obs), cfg)
                rows = trace_unit_vector(
                    engine, obs.farms[player], obs.private, act, step=step, cfg=dict(cfg)
                )
                callbacks += 1
                for row in rows:
                    op = row["op"]
                    if op == "PASS":
                        continue
                    nonpass += 1
                    stat = by_op.setdefault(op, {"total": 0, "changed": 0, "noop": 0})
                    stat["total"] += 1
                    stat["changed"] += int(row["changed"])
                    stat["noop"] += int(not row["changed"])
                    if row["same_target_successful_predecessor"] is not None:
                        same_target.append({
                            "step": step,
                            "actor_index": row["actor_index"],
                            "predecessor_actor_index": row["same_target_successful_predecessor"],
                            "position": row["position"],
                            "op": op,
                            "raw_action": row["raw_action"],
                        })
            else:
                act = engine.starter_agent(copy.deepcopy(state[player].observation))
            actions.append(act)
        for player, act in enumerate(actions):
            state[player].action = act
        engine.interpreter(state, env)
        if all(s.status == "DONE" for s in state):
            break

    return {
        "schema": "titan-v4-unit-action-efficacy-cell/v1",
        "source": {
            "artifact_id": ARTIFACT_ID,
            "inner_tar_sha256": INNER_TAR_SHA256,
            "engine_git_blob": ENGINE_GIT_BLOB,
            "main_git_blob": MAIN_GIT_BLOB,
        },
        "seed": int(seed),
        "seat": int(seat),
        "callbacks": callbacks,
        "nonpass_unit_actions": nonpass,
        "by_op": by_op,
        "same_target_predecessor_noops": same_target,
        "scores": [s.reward for s in state],
    }


def main_cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--package", type=Path, required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--seat", type=int, choices=(0, 1), required=True)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    report = run_cell(args.package, args.seed, args.seat)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main_cli()
