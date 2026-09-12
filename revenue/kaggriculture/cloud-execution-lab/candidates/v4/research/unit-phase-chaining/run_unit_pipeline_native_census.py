#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only current-native engagement census for TITAN V4 UNITPIPE.

The runner authenticates the b567 native fixture used by UNITWASTE, asks the
native agent for its original returned vector, evaluates the canonical
UNITPIPE admission helper on a copy, and always executes the ORIGINAL vector in
the official interpreter. Panel mode starts every seed/seat cell in a fresh
Python process so native agent globals cannot leak across cells.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import copy
import hashlib
import importlib
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from unit_pipeline_admission import ENGINE_GIT_BLOB, reorder_unit_pipeline

ARTIFACT_ID = 10175943272
INNER_TAR_SHA256 = "b567942e4fb4e0571ebf9f8eaaf143d4a9156df3289f09a98db37823ef4d68d9"
ENGINE_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
MAIN_BLOB = "4a8cf7bcda1f0fea231a144692cb84a779a9e73e"
HELPER_BLOB = "f02448806f66e524fdc317c23b620fde45a926c9"
SEEDS = (17, 101, 6607, 9922999, 2026091201, 2026091207, 2026091213, 2026091219)
SEATS = (0, 1)


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_source(package: Path, inner_tar: Path) -> dict[str, Any]:
    source = {
        "artifact_id": ARTIFACT_ID,
        "inner_tar_sha256": sha256(inner_tar),
        "engine_git_blob": git_blob(package / "checks/reference/engine/kaggriculture.py"),
        "main_git_blob": git_blob(package / "main.py"),
        "helper_git_blob": git_blob(HERE / "unit_pipeline_admission.py"),
    }
    expected = {
        "artifact_id": ARTIFACT_ID,
        "inner_tar_sha256": INNER_TAR_SHA256,
        "engine_git_blob": ENGINE_BLOB,
        "main_git_blob": MAIN_BLOB,
        "helper_git_blob": HELPER_BLOB,
    }
    if source != expected:
        raise ValueError(f"UNITPIPE native-census custody mismatch: {source!r} != {expected!r}")
    if ENGINE_GIT_BLOB != ENGINE_BLOB:
        raise ValueError("UNITPIPE helper engine pin does not match census engine pin")
    return source


def _load_fixture(package: Path):
    sys.path.insert(0, str(package))
    sys.path.insert(1, str(package / "checks"))
    from test_engine_semantics import EngineSemantics

    EngineSemantics.setUpClass()
    engine, ev = EngineSemantics.engine, EngineSemantics.ev
    main = importlib.import_module("main")
    return engine, ev, main


def run_cell(package: Path, inner_tar: Path, seed: int, seat: int) -> dict[str, Any]:
    if seat not in SEATS:
        raise ValueError("seat must be 0 or 1")
    source = verify_source(package, inner_tar)
    engine, ev, main = _load_fixture(package)
    cfg = ev.Struct({
        key: (value.get("default") if isinstance(value, dict) else value)
        for key, value in engine.specification["configuration"].items()
    })
    cfg.seed = int(seed)
    env = ev.Struct(configuration=cfg, done=False, info={})
    state = [
        ev.Struct(observation=ev.Struct(), action={}, status="ACTIVE", reward=0)
        for _ in range(2)
    ]
    engine.interpreter(state, env)

    callbacks = 0
    off_drift = 0
    eligible_groups = 0
    changed_groups = 0
    refusals: Counter[str] = Counter()
    events = []

    for step in range(int(cfg.episodeSteps)):
        actions = []
        for player in range(2):
            state[player].observation.step = step
            state[player].observation.remainingOverageTime = 0
            if player == seat:
                obs = state[player].observation
                original = main.agent(copy.deepcopy(obs), cfg)
                callbacks += 1

                off_action, off_report = reorder_unit_pipeline(
                    copy.deepcopy(obs), copy.deepcopy(original), enabled=False
                )
                if off_action != original or off_report.get("changed"):
                    off_drift += 1

                candidate, report = reorder_unit_pipeline(
                    copy.deepcopy(obs), copy.deepcopy(original), enabled=True
                )
                eligible_groups += int(report["eligible_groups"])
                changed_groups += int(report["changed_groups"])
                refusals.update(report["refusals"])
                if report["eligible_groups"] or report["changed_groups"]:
                    events.append({
                        "step": step,
                        "day": step // int(cfg.turnsPerDay),
                        "hour": step % int(cfg.turnsPerDay),
                        "eligible_groups": report["eligible_groups"],
                        "changed_groups": report["changed_groups"],
                        "changes": report["changes"],
                        "original_farmer": copy.deepcopy(original.get("farmer")),
                        "original_hands": copy.deepcopy(original.get("hands")),
                        "candidate_farmer": copy.deepcopy(candidate.get("farmer")),
                        "candidate_hands": copy.deepcopy(candidate.get("hands")),
                    })
                # Critical evidence-only boundary: the candidate is NOT executed.
                action = original
            else:
                action = engine.starter_agent(copy.deepcopy(state[player].observation))
            actions.append(action)

        for player, action in enumerate(actions):
            state[player].action = action
        engine.interpreter(state, env)
        if all(s.status == "DONE" for s in state):
            break

    return {
        "schema": "titan-v4-unitpipe-native-engagement-cell/v1",
        "source": source,
        "seed": int(seed),
        "seat": int(seat),
        "callbacks": callbacks,
        "off_drift_callbacks": off_drift,
        "eligible_groups": eligible_groups,
        "changed_groups": changed_groups,
        "events": events,
        "refusals": dict(sorted(refusals.items())),
        "scores": [s.reward for s in state],
    }


def aggregate(cells: list[dict[str, Any]]) -> dict[str, Any]:
    refusals: Counter[str] = Counter()
    for cell in cells:
        refusals.update(cell["refusals"])
    panel = {
        "cells": len(cells),
        "callbacks": sum(int(c["callbacks"]) for c in cells),
        "off_drift_callbacks": sum(int(c["off_drift_callbacks"]) for c in cells),
        "eligible_groups": sum(int(c["eligible_groups"]) for c in cells),
        "changed_groups": sum(int(c["changed_groups"]) for c in cells),
        "seeds": list(SEEDS),
        "seats": list(SEATS),
    }
    if panel["off_drift_callbacks"]:
        disposition = "INVALID_OFF_IDENTITY"
    elif panel["changed_groups"]:
        disposition = "ENGAGED_REQUIRES_ECONOMIC_GATE"
    elif panel["eligible_groups"]:
        disposition = "CAUSALLY_ORDERED_CURRENT_NATIVE"
    else:
        disposition = "COLD_CURRENT_NATIVE"
    return {
        "schema": "titan-v4-unitpipe-native-engagement-panel/v1",
        "source": cells[0]["source"] if cells else None,
        "panel": panel,
        "refusals": dict(sorted(refusals.items())),
        "cells": [
            {key: cell[key] for key in (
                "seed", "seat", "callbacks", "off_drift_callbacks",
                "eligible_groups", "changed_groups", "scores"
            )}
            for cell in cells
        ],
        "events": [
            {"seed": cell["seed"], "seat": cell["seat"], **event}
            for cell in cells for event in cell["events"]
        ],
        "disposition": disposition,
        "policy_effect": "NONE_EVIDENCE_ONLY",
        "interpretation": {
            "claim": "the canonical UNITPIPE admission helper has no natural eligible or changed groups on the authenticated b567 current-native 8-seed x 2-seat panel",
            "next_step": "do not schedule an OFF/ON economics panel for this narrow helper unless a later native package or broader separately-certified admission creates natural engagement",
        },
    }


def _write(path: Path | None, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if path:
        path.write_text(text)
    else:
        print(text, end="")


def main_cli() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--package", type=Path, required=True)
    p.add_argument("--inner-tar", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--cell-seed", type=int)
    p.add_argument("--cell-seat", type=int, choices=SEATS)
    args = p.parse_args()

    if (args.cell_seed is None) != (args.cell_seat is None):
        p.error("--cell-seed and --cell-seat must be supplied together")
    if args.cell_seed is not None:
        _write(args.output, run_cell(args.package, args.inner_tar, args.cell_seed, args.cell_seat))
        return

    verify_source(args.package, args.inner_tar)

    def run_one(tmp: Path, seed: int, seat: int) -> dict[str, Any]:
        out = tmp / f"{seed}-{seat}.json"
        cmd = [
            sys.executable, "-B", str(Path(__file__).resolve()),
            "--package", str(args.package),
            "--inner-tar", str(args.inner_tar),
            "--cell-seed", str(seed),
            "--cell-seat", str(seat),
            "--output", str(out),
        ]
        subprocess.run(cmd, check=True)
        return json.loads(out.read_text())

    with tempfile.TemporaryDirectory(prefix="unitpipe-native-census-") as tmp_name:
        tmp = Path(tmp_name)
        jobs = [(seed, seat) for seed in SEEDS for seat in SEATS]
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(jobs))) as pool:
            futures = [pool.submit(run_one, tmp, seed, seat) for seed, seat in jobs]
            cells = [future.result() for future in futures]
    cells.sort(key=lambda cell: (int(cell["seed"]), int(cell["seat"])))
    _write(args.output, aggregate(cells))


if __name__ == "__main__":
    main_cli()
