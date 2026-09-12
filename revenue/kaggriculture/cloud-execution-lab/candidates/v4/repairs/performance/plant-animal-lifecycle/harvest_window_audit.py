#!/usr/bin/env python3
"""Source-bound harvest/rot window audit for the pinned Kaggriculture engine.

The audit is intentionally mechanics-only.  It does not execute games, infer
current TITAN controller behavior, or make an economic/promotion decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

SCHEMA = "titan.harvest_windows.audit.v1"
OFFICIAL_ENGINE_SHA256 = "bc8a54879ed74e3afff1a5cc907b30181a5a1dcfb8cef9813401f79518e3cbc3"
OFFICIAL_ENGINE_BLOB = "3c202c7ee496b693c12cda45ac6260357c013091"
OFFICIAL_CONFIG_SHA256 = "c72296248915182945b33f925eb4a7bcea25ec55b3be4237a7e36706568e263d"
DEFAULT_TURNS_PER_DAY = 24

# Transcribed from the source whose exact SHA-256 is pinned above.  The tool
# refuses authoritative CLI output when engine bytes do not match that hash.
CROPS: dict[str, dict[str, Any]] = {
    "WHEAT": {"first_yield_day": 2, "max_yield_day": 4, "interval": 0, "max_yield": 6, "ongoing": False},
    "CARROT": {"first_yield_day": 2, "max_yield_day": 3, "interval": 0, "max_yield": 4, "ongoing": False},
    "TOMATO": {"first_yield_day": 8, "max_yield_day": 8, "interval": 1, "max_yield": 4, "ongoing": True},
    "STRAWBERRY": {"first_yield_day": 10, "max_yield_day": 10, "interval": 2, "max_yield": 4, "ongoing": True},
    "MELON": {"first_yield_day": 10, "max_yield_day": 12, "interval": 0, "max_yield": 6, "ongoing": False},
}


class AuditError(ValueError):
    """Input/provenance error; authoritative output must fail closed."""


def require(ok: bool, message: str) -> None:
    if not ok:
        raise AuditError(message)


def strict_positive_int(value: Any, name: str) -> int:
    require(type(value) is int and value > 0, f"{name}: expected positive integer, not bool/float")
    return value


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_engine(path: Path, expected_sha256: str = OFFICIAL_ENGINE_SHA256) -> str:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise AuditError(f"engine unreadable: {exc}") from exc
    actual = sha256_bytes(data)
    require(actual == expected_sha256,
            f"engine SHA-256 mismatch: expected {expected_sha256}, got {actual}")
    return actual


def _ceil_div(n: int, d: int) -> int:
    return (n + d - 1) // d


def _decay_timeline(mls: int, yield_at_mls: int) -> dict[str, Any]:
    require(yield_at_mls > 0, "yield_at_mls must be positive")
    decay_steps = [mls + 2 * i for i in range(yield_at_mls)]
    return {
        "yield_at_mls": yield_at_mls,
        # Unit actions execute before _decay_plants, so MLS itself is harvestable.
        "last_full_yield_harvest_action_step": mls,
        "first_reduced_yield_observable_callback_step": mls + 1,
        "decay_action_steps_if_never_harvested": decay_steps,
        "last_positive_yield_harvest_action_step": decay_steps[-1],
        "first_weed_observable_callback_step": decay_steps[-1] + 1,
    }


def _nonongoing(crop: str, cd: dict[str, Any], tpd: int) -> dict[str, Any]:
    max_day = int(cd["max_yield_day"])
    max_yield = int(cd["max_yield"])
    water_start = (max_day + 1) // 2
    water_days = list(range(water_start, max_day + 1))
    mls = (max_day + 1) * tpd  # planted_day=0

    # Initial yield is 1. WATER in the eligible window adds +2 when fertilized,
    # otherwise +1.  Mutation occurs during the unit action itself.
    perfect_needed = _ceil_div(max_yield - 1, 2)
    perfect_full_day = water_start + perfect_needed - 1
    perfect_reaches_full = perfect_full_day <= max_day
    perfect_attain = perfect_full_day * tpd if perfect_reaches_full else None
    perfect_observe = perfect_attain + 1 if perfect_attain is not None else None
    perfect_yield = min(max_yield, 1 + 2 * len(water_days))

    water_only_needed = max_yield - 1
    water_only_full_day = water_start + water_only_needed - 1
    water_only_reaches_full = water_only_full_day <= max_day
    water_only_attain = water_only_full_day * tpd if water_only_reaches_full else None
    water_only_observe = water_only_attain + 1 if water_only_attain is not None else None
    water_only_yield = min(max_yield, 1 + len(water_days))

    return {
        "crop": crop,
        "ongoing": False,
        "max_yield": max_yield,
        "max_yield_day": max_day,
        "water_yield_window_days_inclusive": [water_start, max_day],
        "max_lifespan_step": mls,
        "perfect_water_and_fertilizer": {
            "earliest_full_yield_attainable_during_service_action_step": perfect_attain,
            "earliest_full_yield_observable_callback_step": perfect_observe,
            "full_yield_callback_interval_inclusive": ([perfect_observe, mls]
                                                        if perfect_observe is not None else None),
            **_decay_timeline(mls, perfect_yield),
        },
        "water_without_fertilizer": {
            "earliest_full_yield_attainable_during_service_action_step": water_only_attain,
            "earliest_full_yield_observable_callback_step": water_only_observe,
            "full_yield_callback_interval_inclusive": ([water_only_observe, mls]
                                                        if water_only_observe is not None else None),
            **_decay_timeline(mls, water_only_yield),
        },
    }


def _ongoing(crop: str, cd: dict[str, Any], tpd: int) -> dict[str, Any]:
    first = int(cd["first_yield_day"])
    interval = int(cd["interval"])
    max_yield = int(cd["max_yield"])
    require(interval > 0, f"{crop}: ongoing crop must have positive interval")

    event_days = [first + interval * i for i in range(max_yield)]
    event_steps = [day * tpd for day in event_days]
    last_event_day = event_days[-1]
    # On the max_yield-th production event, daily refresh sets MLS to
    # (next_day + 1)*TPD.  next_day is the production-event day.
    mls = (last_event_day + 1) * tpd

    perfect_event_index = _ceil_div(max_yield, 2) - 1
    perfect_full_step = event_steps[perfect_event_index]
    water_only_full_step = event_steps[max_yield - 1]

    perfect_yield = max_yield
    water_only_yield = max_yield
    return {
        "crop": crop,
        "ongoing": True,
        "max_yield": max_yield,
        "first_yield_day": first,
        "production_interval_days": interval,
        "production_event_observable_callback_steps": event_steps,
        "max_lifespan_step": mls,
        "perfect_water_and_fertilizer": {
            "earliest_full_yield_observable_callback_step": perfect_full_step,
            "full_yield_callback_interval_inclusive": [perfect_full_step, mls],
            **_decay_timeline(mls, perfect_yield),
        },
        "water_without_fertilizer": {
            "earliest_full_yield_observable_callback_step": water_only_full_step,
            "full_yield_callback_interval_inclusive": [water_only_full_step, mls],
            **_decay_timeline(mls, water_only_yield),
        },
    }


def build_report(*, turns_per_day: int = DEFAULT_TURNS_PER_DAY,
                 engine_sha256: str = OFFICIAL_ENGINE_SHA256) -> dict[str, Any]:
    tpd = strict_positive_int(turns_per_day, "turns_per_day")
    require(engine_sha256 == OFFICIAL_ENGINE_SHA256,
            "report refuses unpinned engine identity")

    crops = []
    for crop, cd in CROPS.items():
        crops.append(_ongoing(crop, cd, tpd) if cd["ongoing"] else _nonongoing(crop, cd, tpd))

    return {
        "schema": SCHEMA,
        "engine_provenance": {
            "sha256": engine_sha256,
            "git_blob": OFFICIAL_ENGINE_BLOB,
            "config_sha256": OFFICIAL_CONFIG_SHA256,
            "turns_per_day": tpd,
        },
        "assumptions": {
            "planted_day": 0,
            "no_harvest_before_reported_window": True,
            "maintenance": "watered often enough to avoid consecutive-unwatered weed; service profiles differ only by fertilizer bonus",
            "phase_order": "unit actions -> market/town -> _decay_plants -> end-of-day plant refresh",
            "same_step_note": "for nonongoing crops a WATER action can attain max yield before later unit actions in the same interpreter step; the next callback is the first order-independent observation of that yield",
            "economics": "NOT_ASSESSED: market prices and opportunity costs are outside this mechanics-only audit",
        },
        "drought_guard": {
            "planting_state_consecutive_unwatered": 1,
            "weed_condition": "end-of-day consecutive_unwatered >= 2",
            "warning": "rot windows assume maintenance watering; drought can convert a plant to WEED earlier",
        },
        "crops": crops,
        "current_v4_schedule_census": {
            "status": "NOT_ASSESSED",
            "reason": "CANONICAL.json binds the current release archive by hash, but no verified source-to-artifact binding for the authored current controller was available; stale round controller copies are intentionally not substituted",
        },
        "promotion_decision": "NOT_ASSESSED",
    }


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--engine", required=True, type=Path,
                   help="path to the pinned official kaggriculture.py")
    p.add_argument("--output", type=Path)
    p.add_argument("--turns-per-day", type=int, default=DEFAULT_TURNS_PER_DAY)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        tpd = strict_positive_int(args.turns_per_day, "turns_per_day")
        engine_sha = verify_engine(args.engine)
        report = build_report(turns_per_day=tpd, engine_sha256=engine_sha)
        encoded = json.dumps(report, sort_keys=True, indent=2) + "\n"
        if args.output:
            args.output.write_text(encoded, encoding="utf-8")
        else:
            sys.stdout.write(encoded)
        return 0
    except (AuditError, OSError) as exc:
        sys.stderr.write(f"harvest-window-audit: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
