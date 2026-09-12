#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact EOD weed-stream -> town-shop RNG coupling model for TITAN V4 research.

Official Kaggriculture seeds one random.Random per end of day, spends it on
farm-0 weed trials, then farm-1 weed trials, then on the next public shop
unlock. _spawn_weeds draws exactly once for every tile that is empty when the
scan begins. Therefore the shop draw depends on total empty tiles across both
farms, regardless of weedSpawnChance.

Research / causal-integrity oracle only: no gameplay policy or live seed exploit.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Sequence

ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
RNG_SEED_MULTIPLIER = 1_000_003
DEFAULT_SHOP_UNLOCK_INTERVAL = 3
MAX_SHOP_INSTANCES = 8
SHOPS = tuple(sorted((
    "BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT", "YARN_STORE",
    "ICE_CREAM_SHOP", "PET_CAFE", "SMOOTHIE_SHOP", "FARMERS_MARKET",
)))
_DECOUPLED_DOMAIN = 0x53484F50


def git_blob(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def verify_engine_source(path: str | Path) -> str:
    actual = git_blob(Path(path).read_bytes())
    if actual != ENGINE_GIT_BLOB:
        raise ValueError(
            f"engine source drift: expected {ENGINE_GIT_BLOB}, got {actual}"
        )
    return actual


def _nonnegative_int(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a non-negative exact int")
    return value


def normalize_empty_counts(values: Sequence[int]) -> tuple[int, ...]:
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("empty_counts must be a non-empty list/tuple")
    return tuple(
        _nonnegative_int(value, f"empty_counts[{i}]")
        for i, value in enumerate(values)
    )


def weed_rng_draw_count(empty_counts: Sequence[int]) -> int:
    """Exact count of rng.random() calls made by all weed scans."""
    return sum(normalize_empty_counts(empty_counts))


def official_shop_projection(
    *,
    seed: int,
    day: int,
    empty_counts: Sequence[int],
    next_shop_count: int = 0,
    shop_unlock_interval: int = DEFAULT_SHOP_UNLOCK_INTERVAL,
) -> str | None:
    """Project the official EOD shop choice from pre-weed empty-tile counts."""
    seed = _nonnegative_int(seed, "seed")
    day = _nonnegative_int(day, "day")
    next_shop_count = _nonnegative_int(next_shop_count, "next_shop_count")
    if type(shop_unlock_interval) is not int or shop_unlock_interval <= 0:
        raise ValueError("shop_unlock_interval must be a positive exact int")
    next_day = day + 1
    if next_day % shop_unlock_interval != 0:
        return None
    if next_shop_count >= MAX_SHOP_INSTANCES:
        return None
    rng = random.Random((seed * RNG_SEED_MULTIPLIER) ^ day)
    for _ in range(weed_rng_draw_count(empty_counts)):
        rng.random()
    return rng.choice(SHOPS)


def decoupled_shop_control(
    *,
    seed: int,
    day: int,
    next_shop_count: int = 0,
    shop_unlock_interval: int = DEFAULT_SHOP_UNLOCK_INTERVAL,
) -> str | None:
    """Counterfactual independent shop RNG, never an official-engine claim."""
    seed = _nonnegative_int(seed, "seed")
    day = _nonnegative_int(day, "day")
    next_shop_count = _nonnegative_int(next_shop_count, "next_shop_count")
    if type(shop_unlock_interval) is not int or shop_unlock_interval <= 0:
        raise ValueError("shop_unlock_interval must be a positive exact int")
    next_day = day + 1
    if next_day % shop_unlock_interval != 0:
        return None
    if next_shop_count >= MAX_SHOP_INSTANCES:
        return None
    rng = random.Random(
        ((seed * RNG_SEED_MULTIPLIER) ^ day) ^ _DECOUPLED_DOMAIN
    )
    return rng.choice(SHOPS)


def compare_pair(
    *,
    seed: int,
    day: int,
    baseline_empty_counts: Sequence[int],
    candidate_empty_counts: Sequence[int],
    next_shop_count: int = 0,
    shop_unlock_interval: int = DEFAULT_SHOP_UNLOCK_INTERVAL,
) -> dict:
    baseline = normalize_empty_counts(baseline_empty_counts)
    candidate = normalize_empty_counts(candidate_empty_counts)
    base_draws = weed_rng_draw_count(baseline)
    cand_draws = weed_rng_draw_count(candidate)
    base_shop = official_shop_projection(
        seed=seed, day=day, empty_counts=baseline,
        next_shop_count=next_shop_count,
        shop_unlock_interval=shop_unlock_interval,
    )
    cand_shop = official_shop_projection(
        seed=seed, day=day, empty_counts=candidate,
        next_shop_count=next_shop_count,
        shop_unlock_interval=shop_unlock_interval,
    )
    ctl_a = decoupled_shop_control(
        seed=seed, day=day, next_shop_count=next_shop_count,
        shop_unlock_interval=shop_unlock_interval,
    )
    ctl_b = decoupled_shop_control(
        seed=seed, day=day, next_shop_count=next_shop_count,
        shop_unlock_interval=shop_unlock_interval,
    )
    unlock_due = base_shop is not None
    diverged = bool(unlock_due and base_shop != cand_shop)
    return {
        "schema": "titan.v4.town-rng-pair/v1",
        "engine_git_blob": ENGINE_GIT_BLOB,
        "seed": seed,
        "day": day,
        "baseline_empty_counts": list(baseline),
        "candidate_empty_counts": list(candidate),
        "baseline_weed_rng_draws": base_draws,
        "candidate_weed_rng_draws": cand_draws,
        "rng_cursor_shift": cand_draws - base_draws,
        "unlock_due": unlock_due,
        "baseline_shop": base_shop,
        "candidate_shop": cand_shop,
        "shop_diverged": diverged,
        "causal_gate": (
            "ENVIRONMENT_PATH_DIVERGED"
            if diverged else "NO_SHOP_DIVERGENCE_ON_THIS_CELL"
        ),
        "decoupled_control_baseline_shop": ctl_a,
        "decoupled_control_candidate_shop": ctl_b,
        "decoupled_control_equal": ctl_a == ctl_b,
        "weed_chance_affects_cursor": False,
        "policy_claim": False,
        "economic_claim": False,
        "live_seed_targeting_claim": False,
    }


def find_coupling_witness(
    *,
    day: int = 2,
    baseline_total_empty: int = 40,
    delta: int = 1,
    seed_limit: int = 10_000,
) -> dict:
    day = _nonnegative_int(day, "day")
    baseline_total_empty = _nonnegative_int(
        baseline_total_empty, "baseline_total_empty"
    )
    seed_limit = _nonnegative_int(seed_limit, "seed_limit")
    if type(delta) is not int or delta == 0:
        raise ValueError("delta must be a non-zero exact int")
    candidate_total = baseline_total_empty + delta
    if candidate_total < 0:
        raise ValueError("candidate total empties must be non-negative")
    for seed in range(seed_limit):
        base_shop = official_shop_projection(
            seed=seed, day=day, empty_counts=[baseline_total_empty]
        )
        cand_shop = official_shop_projection(
            seed=seed, day=day, empty_counts=[candidate_total]
        )
        if base_shop is not None and base_shop != cand_shop:
            return {
                "seed": seed,
                "day": day,
                "baseline_total_empty": baseline_total_empty,
                "candidate_total_empty": candidate_total,
                "baseline_shop": base_shop,
                "candidate_shop": cand_shop,
            }
    raise ValueError("no coupling witness found in requested seed range")


def run_probe() -> dict:
    equal_total = compare_pair(
        seed=1, day=2,
        baseline_empty_counts=[13, 27],
        candidate_empty_counts=[27, 13],
    )
    changed_total = compare_pair(
        seed=1, day=2,
        baseline_empty_counts=[20, 20],
        candidate_empty_counts=[20, 21],
    )
    return {
        "schema": "titan.v4.town-rng-coupling/v1",
        "engine_git_blob": ENGINE_GIT_BLOB,
        "mechanism": (
            "shared EOD RNG is consumed by per-empty-tile weed trials for both "
            "farms before the public shop choice"
        ),
        "equal_total_seat_swap_control": equal_total,
        "changed_total_witness": changed_total,
        "first_search_witness": find_coupling_witness(
            day=2, baseline_total_empty=40, delta=1, seed_limit=100
        ),
        "gate_rule": (
            "For paired policy/economic gates, compare town.unlocked_shops at "
            "every EOD before attributing downstream market/margin divergence "
            "to the candidate. First shop divergence means the pair has entered "
            "different public environment paths; report separately or rerun "
            "with a controlled shop schedule."
        ),
        "weed_spawn_chance_zero_removes_coupling": False,
        "source_claim": True,
        "policy_claim": False,
        "economic_claim": False,
        "live_seed_targeting_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    verify_engine_source(args.engine)
    text = json.dumps(run_probe(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
