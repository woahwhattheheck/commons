#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact-engine differential for ROWSHED mirror lockstep assignment evidence.

The checker captures and authenticates the official engine and ROWSHED helper
bytes before either module is executed.  All subsequent proof work runs from
those captured buffers; the repository paths are never reopened as controls.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[4]
ENGINE = LAB / "reference" / "engine" / "kaggriculture.py"
HELPER = HERE / "mirror_collision_value.py"
ENGINE_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
HELPER_BLOB = "90052d735316461c7b3320a7e968dcddbb2c364e"


class CheckError(RuntimeError):
    pass


def git_blob_sha_bytes(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def capture(path: Path, expected_blob: str, label: str) -> tuple[bytes, str]:
    """Read one control once and authenticate that exact captured buffer."""
    try:
        data = path.read_bytes()
    except OSError as error:
        raise CheckError(f"cannot capture {label}: {path}") from error
    actual = git_blob_sha_bytes(data)
    if actual != expected_blob:
        raise CheckError(
            f"{label} drift: expected {expected_blob}, got {actual}"
        )
    return data, actual


def load_captured(name: str, path: Path, data: bytes) -> ModuleType:
    """Compile/exec an already-authenticated buffer without reopening its path."""
    module = ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    module.__loader__ = None
    previous = sys.modules.get(name)
    had_previous = name in sys.modules
    sys.modules[name] = module
    try:
        exec(compile(data, str(path), "exec"), module.__dict__)
    except Exception as error:  # checker boundary: convert control-load failure
        raise CheckError(f"cannot execute captured {path.name}") from error
    finally:
        if had_previous:
            sys.modules[name] = previous
        else:
            sys.modules.pop(name, None)
    return module


def run_cell(engine, helper, *, item: str, inventory: int, quantity: int) -> dict:
    market = engine._new_market()
    market["inventory"][item] = inventory
    engine._refresh_prices(market)
    farms = [engine._new_farm(10, 3000) for _ in range(2)]
    privates = [engine._new_private() for _ in range(2)]
    for private in privates:
        private["shed"][item] = quantity

    obs0 = SimpleNamespace(market=market, farms=farms)
    states = []
    for player in range(2):
        observation = obs0 if player == 0 else SimpleNamespace()
        observation.private = privates[player]
        states.append(
            SimpleNamespace(
                observation=observation,
                action={
                    "farmer": ["PASS"],
                    "hands": [],
                    "market": [["SELL", item, quantity]],
                },
            )
        )
    env = SimpleNamespace(
        configuration={
            "boardSize": 10,
            "maxMarketOrdersPerTurn": 10,
            "farmHandCostMult": 1,
            "shedCapacity": 100,
        }
    )

    before_money = [farm["money"] for farm in farms]
    engine._process_market(states, env)
    cash = [int(farms[i]["money"] - before_money[i]) for i in range(2)]
    score = helper.mirror_collision_score(
        item=item,
        public_inventory=inventory,
        fillable=quantity,
        price_fn=engine.market_price,
    )
    expected = score["aligned_lockstep_cash"]
    if cash != [expected, expected]:
        raise CheckError(
            f"aligned cash mismatch {item} inv={inventory} q={quantity}: "
            f"engine={cash} helper={expected}"
        )
    if market["inventory"][item] != score["after_aligned_pair_inventory"]:
        raise CheckError(
            f"aligned inventory mismatch {item}: engine={market['inventory'][item]} "
            f"helper={score['after_aligned_pair_inventory']}"
        )
    if any(private["shed"][item] != 0 for private in privates):
        raise CheckError(f"mirror SELL did not consume full {item} lots")
    return {
        "item": item,
        "public_inventory": inventory,
        "quantity": quantity,
        "aligned_cash": expected,
        "ending_inventory": market["inventory"][item],
        "promote_gain": score["promote_gain"],
        "demote_loss": score["demote_loss"],
    }


def run() -> dict:
    # Capture and authenticate BOTH controls before either one executes.  The
    # buffers below are the sole control authority for the rest of this run.
    engine_bytes, actual_engine = capture(ENGINE, ENGINE_BLOB, "engine")
    helper_bytes, actual_helper = capture(HELPER, HELPER_BLOB, "helper")
    engine = load_captured("_rowshed_lockstep_engine", ENGINE, engine_bytes)
    helper = load_captured("_rowshed_lockstep_helper", HELPER, helper_bytes)
    if helper.ENGINE_GIT_BLOB != ENGINE_BLOB:
        raise CheckError("helper engine pin drift")

    cells = [
        run_cell(engine, helper, item="CARROT", inventory=10_000, quantity=5),
        run_cell(engine, helper, item="WOOL", inventory=10_000, quantity=5),
        run_cell(engine, helper, item="MELON", inventory=10_025, quantity=60),
        run_cell(engine, helper, item="WOOL", inventory=10_025, quantity=30),
    ]
    expected = [
        ("CARROT", 165, 3, 5),
        ("WOOL", 993, 5, 8),
        ("MELON", 10052, 2988, 3095),
        ("WOOL", 1660, 1495, 1576),
    ]
    got = [
        (r["item"], r["aligned_cash"], r["promote_gain"], r["demote_loss"])
        for r in cells
    ]
    if got != expected:
        raise CheckError(f"pinned lockstep witness drift: {got!r}")

    return {
        "status": "PASS",
        "scope": "official _process_market identical-row lockstep baseline",
        "engine_git_blob": actual_engine,
        "helper_git_blob": actual_helper,
        "controls_executed_from_captured_bytes": True,
        "cells": cells,
        "carrot_wool_swap_edge": 5 - 5,
        "hosted_wool_melon_swap_edge": 2988 - 1576,
    }


def main() -> int:
    print(json.dumps(run(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
