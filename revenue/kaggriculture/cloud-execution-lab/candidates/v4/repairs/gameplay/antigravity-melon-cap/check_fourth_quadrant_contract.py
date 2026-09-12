#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exercise real FourthQuadrant producer -> MELON filter -> install identity.

Usage:
    python check_fourth_quadrant_contract.py --package /path/to/package

The package must contain fourth_quadrant.py. No network access is used.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import melon_cap as M

EXPECTED_FOURTH_QUADRANT_BLOB = "57ffe172a5a5ebf5b57132319731aa367b9dc7f5"


def _git_blob(data: bytes) -> str:
    import hashlib
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def _load(path: Path):
    data = path.read_bytes()
    blob = _git_blob(data)
    if blob != EXPECTED_FOURTH_QUADRANT_BLOB:
        raise SystemExit(f"unexpected fourth_quadrant.py blob: {blob}")
    spec = importlib.util.spec_from_file_location("canonical_fourth_quadrant", path)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load fourth_quadrant.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Mechanics:
    CROPS = {
        "CARROT": {"seed": 1},
        "TOMATO": {"seed": 1},
        "MELON": {"seed": 1},
    }

    @staticmethod
    def _hire_cost(_hires: int, _mult: int) -> int:
        return 1


def observation():
    tiles = [
        ["LOCKED" if x >= 5 and y >= 5 else None for x in range(10)]
        for y in range(10)
    ]
    return {
        "step": 264,
        "player": 0,
        "farms": [{
            "tiles": tiles,
            "unlocked_quadrants": ["NW", "NE", "SW"],
            "hands": [],
            "farmer": [4, 4],
            "sale_counters": {"MELON": 0},
        }],
        "private": {"shed": {"MELON": 0}, "inventories": [{}]},
        "market": {"inventory": {"MELON": 10_000}},
    }


def configuration():
    return {
        "maxMarketOrdersPerTurn": 10,
        "farmHandCostMult": 1,
        "episodeSteps": 720,
        "turnsPerDay": 24,
        "shedCapacity": 100,
    }


class Controller:
    def __init__(self):
        self.R = {"A": [{} for _ in range(720)]}
        self.cur = "A"

    @staticmethod
    def act(_obs):
        return {"farmer": ["PASS"], "market": []}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    args = parser.parse_args()
    Q = _load(args.package / "fourth_quadrant.py")

    obs = observation()
    raw = Q.proposals(Mechanics(), obs, {"A": [{} for _ in range(720)]}, "A", configuration())
    melon = [p for p in raw if p.get("crop") == "MELON"]
    five = next(p for p in melon if len(p["tiles"]) == 5)
    four = next(p for p in melon if len(p["tiles"]) == 4)
    assert M.executable_melon_plants(five) == 5
    assert M.executable_melon_plants(four) == 4
    filtered = M.filter_proposals([five, four], obs)
    assert filtered == [four]
    assert filtered[0] is four

    selected = {}
    def admit(_m, runtime_obs, _config, _routes, options):
        candidates = [p for p in M.filter_proposals(options, runtime_obs)
                      if isinstance(p, dict) and p.get("crop") == "MELON"]
        chosen = max(candidates, key=M.executable_melon_plants)
        selected["proposal"] = chosen
        return chosen

    controller = Controller()
    quadrant = Q.FourthQuadrant(Mechanics(), admit)
    quadrant.configure(configuration())
    quadrant.install(controller)
    controller.act(obs)
    chosen = selected["proposal"]
    assert quadrant.pending is chosen
    assert M.executable_melon_plants(chosen) == 4
    assert chosen in raw or len(chosen["tiles"]) == 4
    print("OK: real producer -> atomic filter -> FourthQuadrant.install selected 4-plant original proposal")


if __name__ == "__main__":
    main()
