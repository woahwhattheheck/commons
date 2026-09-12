#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Authenticated current-native census for TITAN V4 unit-phase chaining.

One process must trace one seed/seat. This tool executes the exact native agent
from a pinned release artifact, replays only its returned unit vector on private
copies through the pinned official engine, and calls the canonical default-OFF
UNITPIPE admission helper for natural engagement counts. It never mutates the
artifact, production source, defaults, or returned actions used by the game.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from unit_pipeline_admission import reorder_unit_pipeline

ENGINE_REL = Path("checks/reference/engine/kaggriculture.py")
MAIN_REL = Path("main.py")
CONFIG_REL = Path("TITAN-CONFIG.json")
ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
MAIN_GIT_BLOB = "4a8cf7bcda1f0fea231a144692cb84a779a9e73e"
CONFIG_GIT_BLOB = "3a3bef83899d3010fad623b628d9e95d9978111b"
ADMISSION_GIT_BLOB = "f02448806f66e524fdc317c23b620fde45a926c9"
ARTIFACT_ID = 10175943272
INNER_TAR_SHA256 = "b567942e4fb4e0571ebf9f8eaaf143d4a9156df3289f09a98db37823ef4d68d9"
CHAIN_KEYS = (
    "DIG_PLANT",
    "PLANT_WATER",
    "DIG_PLANT_WATER",
    "HARVEST_PLANT",
    "HARVEST_PLANT_WATER",
    "FERTILIZE_WATER_FRESH_BONUS",
    "BUILD_PLACE",
)


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _verify(path: Path, expected: str, label: str) -> None:
    got = git_blob_sha(path.read_bytes())
    if got != expected:
        raise ValueError(f"{label} Git blob mismatch: expected {expected}, got {got}")


def verify_sources(package: Path) -> None:
    _verify(package / ENGINE_REL, ENGINE_GIT_BLOB, "official engine")
    _verify(package / MAIN_REL, MAIN_GIT_BLOB, "native main.py")
    _verify(package / CONFIG_REL, CONFIG_GIT_BLOB, "native TITAN-CONFIG.json")
    _verify(HERE / "unit_pipeline_admission.py", ADMISSION_GIT_BLOB, "canonical admission helper")


def load_fixture(package: Path):
    verify_sources(package)
    sys.path.insert(0, str(package))
    sys.path.insert(1, str(package / "checks"))
    from test_engine_semantics import EngineSemantics

    EngineSemantics.setUpClass()
    engine, ev = EngineSemantics.engine, EngineSemantics.ev
    main = importlib.import_module("main")
    return engine, ev, main


def _op(row: Any) -> str:
    if isinstance(row, list) and row and isinstance(row[0], str):
        return row[0]
    return "<MALFORMED>"


def _tile(farm: dict[str, Any], position: tuple[int, int]) -> Any:
    x, y = position
    return copy.deepcopy(farm["tiles"][y][x])


def _effective_rows(rows: list[Any], private: dict[str, Any]) -> list[Any]:
    demand: Counter[str] = Counter()
    for row in rows:
        if isinstance(row, list) and len(row) >= 2 and row[0] == "PLANT":
            demand[row[1]] += 1
    seeds = private.get("seeds", {})
    blocked = {crop for crop, count in demand.items() if count > seeds.get(crop, 0)}
    return [
        ["PASS"]
        if isinstance(row, list) and len(row) >= 2 and row[0] == "PLANT" and row[1] in blocked
        else row
        for row in rows
    ]


def analyze_unit_vector(engine, farm0: dict[str, Any], private0: dict[str, Any],
                        action: dict[str, Any], *, step: int, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Return source-real ordered chain events from one returned unit vector."""
    farm = copy.deepcopy(farm0)
    private = copy.deepcopy(private0)
    raw = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
    rows = _effective_rows(raw, private)
    positions = [tuple(farm["farmer"]), *[tuple(p) for p in farm.get("hands", [])]]
    board_size = int(cfg.get("boardSize", 10))
    turns_per_day = max(1, int(cfg.get("turnsPerDay", 24)))
    shed_capacity = int(cfg.get("shedCapacity", 100))
    day = int(step) // turns_per_day
    initial_tiles = {p: _tile(farm0, p) for p in set(positions[: len(rows)])}
    successful: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    events: list[dict[str, Any]] = []

    for actor, row in enumerate(rows):
        if actor >= len(positions):
            break
        position = positions[actor]
        before_tile = _tile(farm, position)
        before_farm = copy.deepcopy(farm)
        before_private = copy.deepcopy(private)
        engine._apply_unit_action(
            farm, private, actor, row, board_size, day, turns_per_day, shed_capacity
        )
        changed = farm != before_farm or private != before_private
        if not changed:
            continue
        after_tile = _tile(farm, position)
        current = _op(row)
        prior = list(successful[position])

        if current == "PLANT":
            digs = [event for event in prior if event["op"] == "DIG"]
            harvests = [event for event in prior if event["op"] == "HARVEST"]
            if digs:
                events.append({"chain": "DIG_PLANT", "position": list(position),
                               "actors": [digs[-1]["actor"], actor], "crop": row[1]})
            if harvests:
                events.append({"chain": "HARVEST_PLANT", "position": list(position),
                               "actors": [harvests[-1]["actor"], actor], "crop": row[1]})

        elif current == "WATER":
            plants = [event for event in prior if event["op"] == "PLANT"]
            fertilizers = [event for event in prior if event["op"] == "FERTILIZE"]
            if plants:
                plant = plants[-1]
                crop = after_tile.get("crop") if isinstance(after_tile, dict) else None
                events.append({"chain": "PLANT_WATER", "position": list(position),
                               "actors": [plant["actor"], actor], "crop": crop})
                digs = [event for event in prior if event["op"] == "DIG" and event["actor"] < plant["actor"]]
                harvests = [event for event in prior if event["op"] == "HARVEST" and event["actor"] < plant["actor"]]
                if digs:
                    events.append({"chain": "DIG_PLANT_WATER", "position": list(position),
                                   "actors": [digs[-1]["actor"], plant["actor"], actor], "crop": crop})
                if harvests:
                    events.append({"chain": "HARVEST_PLANT_WATER", "position": list(position),
                                   "actors": [harvests[-1]["actor"], plant["actor"], actor], "crop": crop})
            if fertilizers and isinstance(before_tile, dict) and isinstance(after_tile, dict):
                initial = initial_tiles.get(position)
                initial_until = initial.get("fertilized_until_day", -1) if isinstance(initial, dict) else -1
                before_yield, after_yield = before_tile.get("yield_units"), after_tile.get("yield_units")
                if (
                    isinstance(before_yield, (int, float))
                    and isinstance(after_yield, (int, float))
                    and after_yield - before_yield > 1
                    and initial_until < day
                ):
                    events.append({"chain": "FERTILIZE_WATER_FRESH_BONUS",
                                   "position": list(position),
                                   "actors": [fertilizers[-1]["actor"], actor],
                                   "yield_delta": after_yield - before_yield})

        elif current == "PLACE" and len(row) >= 2:
            animal = row[1]
            structure = "COOP" if animal == "GOOSE" else ("PASTURE" if animal in {"COW", "SHEEP"} else None)
            if structure is not None:
                builds = [event for event in prior if event["op"] == f"BUILD_{structure}"]
                if builds:
                    events.append({"chain": "BUILD_PLACE", "position": list(position),
                                   "actors": [builds[-1]["actor"], actor],
                                   "animal": animal, "structure": structure})

        successful[position].append({"actor": actor, "op": current})
    return events


def run_cell(package: Path, seed: int, seat: int) -> dict[str, Any]:
    if seat not in (0, 1):
        raise ValueError("seat must be 0 or 1")
    engine, ev, main = load_fixture(package)
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

    chains: Counter[str] = Counter()
    admission = Counter({"eligible_groups": 0, "changed_groups": 0})
    callbacks = colocated_callbacks = colocated_groups = 0
    examples: list[dict[str, Any]] = []
    for step in range(int(cfg.episodeSteps)):
        actions = []
        for player in range(2):
            state[player].observation.step = step
            state[player].observation.remainingOverageTime = 0
            if player == seat:
                obs = state[player].observation
                action = main.agent(copy.deepcopy(obs), cfg)
                callbacks += 1
                farm = obs.farms[player]
                positions = [tuple(farm["farmer"]), *[tuple(p) for p in farm.get("hands", [])]]
                occupancy = Counter(positions)
                groups = sum(1 for count in occupancy.values() if count >= 2)
                if groups:
                    colocated_callbacks += 1
                    colocated_groups += groups

                report_obs = {"player": player, "farms": copy.deepcopy(obs.farms),
                              "private": copy.deepcopy(obs.private)}
                _, report = reorder_unit_pipeline(report_obs, copy.deepcopy(action), enabled=True)
                admission["eligible_groups"] += report["eligible_groups"]
                admission["changed_groups"] += report["changed_groups"]
                if report["changes"] and len(examples) < 64:
                    examples.append({"step": step, "kind": "ADMISSION", "changes": report["changes"]})

                events = analyze_unit_vector(
                    engine, farm, obs.private, action, step=step, cfg=dict(cfg)
                )
                for event in events:
                    chains[event["chain"]] += 1
                    if len(examples) < 64:
                        examples.append({"step": step, "kind": "REALIZED_CHAIN", **event})
            else:
                action = engine.starter_agent(copy.deepcopy(state[player].observation))
            actions.append(action)
        for player, action in enumerate(actions):
            state[player].action = action
        engine.interpreter(state, env)
        if all(player.status == "DONE" for player in state):
            break

    return {
        "schema": "titan-v4-unit-phase-chaining-native-cell/v1",
        "source": {
            "artifact_id": ARTIFACT_ID,
            "inner_tar_sha256": INNER_TAR_SHA256,
            "engine_git_blob": ENGINE_GIT_BLOB,
            "main_git_blob": MAIN_GIT_BLOB,
            "config_git_blob": CONFIG_GIT_BLOB,
            "admission_git_blob": ADMISSION_GIT_BLOB,
        },
        "seed": int(seed),
        "seat": int(seat),
        "callbacks": callbacks,
        "colocated_callbacks": colocated_callbacks,
        "colocated_groups": colocated_groups,
        "realized_chains": {key: chains.get(key, 0) for key in CHAIN_KEYS},
        "admission": {
            "eligible_groups": admission["eligible_groups"],
            "changed_groups": admission["changed_groups"],
        },
        "examples": examples,
        "scores": [player.reward for player in state],
    }


def aggregate_cells(paths: list[Path]) -> dict[str, Any]:
    cells = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    if not cells:
        raise ValueError("at least one cell report is required")
    expected_source = cells[0]["source"]
    if any(cell.get("source") != expected_source for cell in cells):
        raise ValueError("cell source identity mismatch")
    chain_totals: Counter[str] = Counter()
    eligible = changed = callbacks = colocated_callbacks = colocated_groups = 0
    summaries = []
    for cell in cells:
        chain_totals.update(cell["realized_chains"])
        eligible += int(cell["admission"]["eligible_groups"])
        changed += int(cell["admission"]["changed_groups"])
        callbacks += int(cell["callbacks"])
        colocated_callbacks += int(cell["colocated_callbacks"])
        colocated_groups += int(cell["colocated_groups"])
        summaries.append({key: cell[key] for key in (
            "seed", "seat", "callbacks", "colocated_callbacks", "colocated_groups",
            "realized_chains", "admission", "scores"
        )})
    all_chain_zero = all(chain_totals.get(key, 0) == 0 for key in CHAIN_KEYS)
    disposition = "COLD_CURRENT_NATIVE_B567" if all_chain_zero and eligible == 0 and changed == 0 else "ENGAGED"
    return {
        "schema": "titan-v4-unit-phase-chaining-native-panel/v1",
        "source": expected_source,
        "panel": {
            "cells": len(cells),
            "callbacks": callbacks,
            "colocated_callbacks": colocated_callbacks,
            "colocated_groups": colocated_groups,
            "seeds": sorted({cell["seed"] for cell in cells}),
            "seats": sorted({cell["seat"] for cell in cells}),
        },
        "realized_chains": {key: chain_totals.get(key, 0) for key in CHAIN_KEYS},
        "admission": {"eligible_groups": eligible, "changed_groups": changed},
        "cells": sorted(summaries, key=lambda item: (item["seed"], item["seat"])),
        "disposition": disposition,
        "policy_effect": "NONE_EVIDENCE_ONLY",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    cell = sub.add_parser("cell")
    cell.add_argument("--package", type=Path, required=True)
    cell.add_argument("--seed", type=int, required=True)
    cell.add_argument("--seat", type=int, choices=(0, 1), required=True)
    cell.add_argument("--output", type=Path)
    panel = sub.add_parser("aggregate")
    panel.add_argument("reports", type=Path, nargs="+")
    panel.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (
        run_cell(args.package, args.seed, args.seat)
        if args.command == "cell"
        else aggregate_cells(args.reports)
    )
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
