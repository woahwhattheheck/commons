"""Execute the annual relay theorem against the exact official engine source.

Run from a Commons checkout.  This script refuses engine blob drift before import.
It is research evidence only; it does not author or activate a TITAN action.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import types
from pathlib import Path

ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
ANNUALS = ("WHEAT", "CARROT", "MELON")

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[3]  # .../cloud-execution-lab
ENGINE = LAB / "reference" / "engine" / "kaggriculture.py"


def _git_blob(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], text=True).strip()


def _load_engine():
    blob = _git_blob(ENGINE)
    if blob != ENGINE_GIT_BLOB:
        raise RuntimeError(f"engine drift: {blob} != {ENGINE_GIT_BLOB}")

    try:
        import kaggle_environments.utils  # noqa: F401
    except Exception:
        pkg = types.ModuleType("kaggle_environments")
        utils = types.ModuleType("kaggle_environments.utils")
        utils.resolve_episode_seed = lambda env: env.info.get("seed", 0)
        pkg.utils = utils
        sys.modules.setdefault("kaggle_environments", pkg)
        sys.modules.setdefault("kaggle_environments.utils", utils)

    spec = importlib.util.spec_from_file_location("relay_official_engine", ENGINE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load official engine")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _world(engine, old_crop: str, new_crop: str, day: int):
    board_size = 10
    tile = (1, 1)
    tiles = [[None for _ in range(board_size)] for _ in range(board_size)]
    planted_day = day - engine.CROPS[old_crop]["first_yield_day"]
    old = engine._new_plant(old_crop, planted_day, 24)
    old["yield_units"] = min(3, engine.CROPS[old_crop]["max_yield"])
    old["watered_today"] = True
    old["consecutive_unwatered"] = 0
    tiles[tile[1]][tile[0]] = old
    farm = {"farmer": [1, 1], "hands": [[1, 1], [1, 1]], "tiles": tiles}
    private = {
        "shed": {},
        "seeds": {crop: (1 if crop == new_crop else 0) for crop in engine.CROPS},
        "inventories": [{}, {}, {}],
    }
    return farm, private, tile


def _run_relay(engine, old_crop: str, new_crop: str):
    day = 12
    farm, private, (x, y) = _world(engine, old_crop, new_crop, day)
    source_units = farm["tiles"][y][x]["yield_units"]

    engine._apply_unit_action(farm, private, 0, ["HARVEST"], 10, day, 24, 100)
    assert farm["tiles"][y][x] is None
    assert private["inventories"][0].get(old_crop) == source_units

    engine._apply_unit_action(farm, private, 1, ["PLANT", new_crop], 10, day, 24, 100)
    planted = farm["tiles"][y][x]
    assert planted["kind"] == "PLANT" and planted["crop"] == new_crop
    assert planted["watered_today"] is False
    assert planted["consecutive_unwatered"] == 1
    assert private["seeds"][new_crop] == 0

    engine._apply_unit_action(farm, private, 2, ["WATER"], 10, day, 24, 100)
    assert farm["tiles"][y][x]["watered_today"] is True

    engine._daily_refresh_plants(farm, day, 24)
    after = farm["tiles"][y][x]
    assert after["kind"] == "PLANT" and after["crop"] == new_crop
    assert after["consecutive_unwatered"] == 0
    assert after["watered_today"] is False
    return {
        "old_crop": old_crop,
        "new_crop": new_crop,
        "harvest_units": source_units,
        "survives_eod": True,
    }


def _run_reversed_control(engine):
    day = 12
    farm, private, (x, y) = _world(engine, "WHEAT", "CARROT", day)
    engine._apply_unit_action(farm, private, 0, ["HARVEST"], 10, day, 24, 100)
    engine._apply_unit_action(farm, private, 1, ["WATER"], 10, day, 24, 100)
    engine._apply_unit_action(farm, private, 2, ["PLANT", "CARROT"], 10, day, 24, 100)
    engine._daily_refresh_plants(farm, day, 24)
    tile = farm["tiles"][y][x]
    assert tile == {"kind": "WEED"}
    return {"order": "HARVEST,WATER,PLANT", "result": "WEED"}


def main() -> int:
    engine = _load_engine()
    rows = []
    for old_crop in ANNUALS:
        for new_crop in ANNUALS:
            rows.append(_run_relay(engine, old_crop, new_crop))
    result = {
        "schema": "titan-v4-annual-relay-rotation-witness/v1",
        "engine_git_blob": ENGINE_GIT_BLOB,
        "positive_cells": rows,
        "reversed_control": _run_reversed_control(engine),
        "promotion_decision": "NOT_ASSESSED",
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
