#!/usr/bin/env python3
"""Source-bound oracle for end-of-day weed RNG -> public town-shop coupling.

Research-only. This module does not mutate TITAN policy/runtime or infer that
the episode seed is observable to an agent.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable, Sequence

ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
ENGINE_SHA256 = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"
def _default_engine_path() -> Path:
    here = Path(__file__).resolve()
    for parent in (here.parent, *here.parents):
        candidate = parent / "reference" / "engine" / "kaggriculture.py"
        if candidate.is_file():
            return candidate
    return here.parent / "_missing_reference_engine.py"


ENGINE_PATH = _default_engine_path()

SHOPS = (
    "BAKERY",
    "BRUNCH_SPOT",
    "FARMERS_MARKET",
    "ICE_CREAM_SHOP",
    "PET_CAFE",
    "PIZZA_SHOP",
    "SMOOTHIE_SHOP",
    "YARN_STORE",
)

_END_OF_DAY_ANCHORS = (
    'rng = random.Random((seed * 1_000_003) ^ day)',
    '_spawn_weeds(farm, board_size, weed_chance, rng)',
    'town["unlocked_shops"].append(rng.choice(sorted(SHOPS)))',
)
_WEED_ANCHOR = 'farm["tiles"][y][x] is None and rng.random() < weed_chance'


def _plain_nonnegative_int(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a plain nonnegative int")
    return value


def authenticate_engine(path: Path = ENGINE_PATH) -> dict[str, str]:
    """Fail closed unless the exact reviewed official engine bytes are present."""
    data = path.read_bytes()
    sha256 = hashlib.sha256(data).hexdigest()
    if sha256 != ENGINE_SHA256:
        raise RuntimeError(
            f"official engine SHA256 drift: expected {ENGINE_SHA256}, got {sha256}"
        )
    text = data.decode("utf-8")
    weed_i = text.find(_WEED_ANCHOR)
    if weed_i < 0:
        raise RuntimeError("official weed RNG anchor missing")
    end_start = text.find("def _end_of_day(")
    end_stop = text.find("\ndef interpreter(", end_start)
    if end_start < 0 or end_stop < 0:
        raise RuntimeError("official _end_of_day source span missing")
    span = text[end_start:end_stop]
    positions = [span.find(anchor) for anchor in _END_OF_DAY_ANCHORS]
    if any(pos < 0 for pos in positions):
        raise RuntimeError("official _end_of_day RNG/shop anchors missing")
    if positions != sorted(positions):
        raise RuntimeError("official _end_of_day RNG/shop order drift")
    return {"git_blob": ENGINE_GIT_BLOB, "sha256": sha256}


def shop_after_vacancy_draws(
    *,
    seed: int,
    day: int,
    empty_tiles_by_farm: Sequence[int],
    shops: Sequence[str] = SHOPS,
) -> str:
    """Model the reviewed RNG cursor contract immediately before shop choice.

    `_spawn_weeds` consumes exactly one `random()` call for every tile that is
    `None` when that farm's weed scan reaches it. Weed probability changes the
    result of the comparison, not whether that draw is consumed.
    """
    seed = _plain_nonnegative_int(seed, "seed")
    day = _plain_nonnegative_int(day, "day")
    if not isinstance(empty_tiles_by_farm, (list, tuple)) or not empty_tiles_by_farm:
        raise ValueError("empty_tiles_by_farm must be a non-empty list/tuple")
    counts = [
        _plain_nonnegative_int(value, f"empty_tiles_by_farm[{index}]")
        for index, value in enumerate(empty_tiles_by_farm)
    ]
    if not isinstance(shops, (list, tuple)) or not shops:
        raise ValueError("shops must be a non-empty list/tuple")
    if any(type(shop) is not str or not shop for shop in shops):
        raise ValueError("shops must contain non-empty strings")
    rng = random.Random((seed * 1_000_003) ^ day)
    for count in counts:
        for _ in range(count):
            rng.random()
    return rng.choice(sorted(shops))


def _install_kaggle_import_stub_if_needed() -> None:
    try:
        import kaggle_environments.utils  # noqa: F401
        return
    except ModuleNotFoundError:
        pass
    pkg = types.ModuleType("kaggle_environments")
    utils = types.ModuleType("kaggle_environments.utils")
    utils.resolve_episode_seed = lambda *args, **kwargs: 0
    pkg.utils = utils
    sys.modules.setdefault("kaggle_environments", pkg)
    sys.modules.setdefault("kaggle_environments.utils", utils)


def load_authenticated_engine(path: Path = ENGINE_PATH):
    authenticate_engine(path)
    _install_kaggle_import_stub_if_needed()
    spec = importlib.util.spec_from_file_location("shopstream_official_engine", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not create official engine import spec")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _state_for_engine(engine, *, filled: tuple[int, int] | None) -> list[SimpleNamespace]:
    board_size = 10
    farms = [engine._new_farm(board_size, 1000), engine._new_farm(board_size, 1000)]
    if filled is not None:
        farm_id, flat_index = filled
        farm_id = _plain_nonnegative_int(farm_id, "filled farm_id")
        flat_index = _plain_nonnegative_int(flat_index, "filled flat_index")
        if farm_id not in (0, 1) or flat_index >= 25:
            raise ValueError("filled coordinate must name one NW 5x5 tile")
        y, x = divmod(flat_index, 5)
        farms[farm_id]["tiles"][y][x] = {"kind": "COOP"}
    privates = [engine._new_private(), engine._new_private()]
    obs0 = SimpleNamespace(
        farms=farms,
        town={"unlocked_shops": []},
        private=privates[0],
    )
    obs1 = SimpleNamespace(private=privates[1])
    return [SimpleNamespace(observation=obs0), SimpleNamespace(observation=obs1)]


def official_shop_unlock(
    *,
    seed: int,
    day: int = 2,
    filled: tuple[int, int] | None = None,
    weed_spawn_chance: float = 0.0,
    engine=None,
) -> str | None:
    """Execute the exact authenticated engine `_end_of_day` shop selection."""
    seed = _plain_nonnegative_int(seed, "seed")
    day = _plain_nonnegative_int(day, "day")
    if engine is None:
        engine = load_authenticated_engine()
    state = _state_for_engine(engine, filled=filled)
    env = SimpleNamespace(
        info={"seed": seed},
        configuration={
            "boardSize": 10,
            "turnsPerDay": 24,
            "weedSpawnChance": float(weed_spawn_chance),
            "shedCapacity": 100,
            "townShopUnlockInterval": 3,
        },
    )
    engine._end_of_day(state, env, day)
    unlocked = state[0].observation.town["unlocked_shops"]
    return unlocked[-1] if unlocked else None


def build_report(*, first_seed: int = 1, last_seed: int = 512) -> dict[str, object]:
    first_seed = _plain_nonnegative_int(first_seed, "first_seed")
    last_seed = _plain_nonnegative_int(last_seed, "last_seed")
    if first_seed == 0 or last_seed < first_seed:
        raise ValueError("seed range must satisfy 1 <= first_seed <= last_seed")
    engine_identity = authenticate_engine()
    engine = load_authenticated_engine()
    changed: list[dict[str, object]] = []
    unchanged = 0
    model_mismatches = 0
    same_total_mismatches = 0
    for seed in range(first_seed, last_seed + 1):
        base = official_shop_unlock(seed=seed, filled=None, engine=engine)
        farm0_filled = official_shop_unlock(seed=seed, filled=(0, 0), engine=engine)
        farm1_filled = official_shop_unlock(seed=seed, filled=(1, 0), engine=engine)

        model_base = shop_after_vacancy_draws(
            seed=seed, day=2, empty_tiles_by_farm=(25, 25)
        )
        model_filled = shop_after_vacancy_draws(
            seed=seed, day=2, empty_tiles_by_farm=(24, 25)
        )
        if (base, farm0_filled) != (model_base, model_filled):
            model_mismatches += 1
        if farm0_filled != farm1_filled:
            same_total_mismatches += 1
        if base != farm0_filled:
            changed.append(
                {
                    "seed": seed,
                    "all_empty": base,
                    "one_static_tile": farm0_filled,
                }
            )
        else:
            unchanged += 1

    return {
        "schema": "titan-v4-shopstream/v1",
        "engine": engine_identity,
        "scope": {
            "day_argument": 2,
            "next_day": 3,
            "town_shop_unlock_interval": 3,
            "weed_spawn_chance": 0.0,
            "baseline_empty_tiles": [25, 25],
            "variant_empty_tiles": [24, 25],
            "seed_range": [first_seed, last_seed],
        },
        "result": {
            "cells": last_seed - first_seed + 1,
            "shop_changed": len(changed),
            "shop_unchanged": unchanged,
            "model_mismatches": model_mismatches,
            "same_total_farm_placement_mismatches": same_total_mismatches,
            "first_witnesses": changed[:32],
        },
        "interpretation": {
            "source_mechanism": (
                "End-of-day empty-tile weed RNG draws advance the same RNG stream "
                "used for public shop choice."
            ),
            "not_claimed": [
                "episode seed is observable to the agent",
                "a live TITAN route can profitably steer the shop",
                "changing tile occupancy is free or safe",
                "this receipt authorizes runtime activation",
            ],
        },
    }


def _main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--first-seed", type=int, default=1)
    parser.add_argument("--last-seed", type=int, default=512)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = build_report(first_seed=args.first_seed, last_seed=args.last_seed)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
