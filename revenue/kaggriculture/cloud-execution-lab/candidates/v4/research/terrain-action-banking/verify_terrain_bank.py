# SPDX-License-Identifier: Apache-2.0
"""Source-bound falsifier for the proposed zero-cost structure weed "action bank".

The claim under test is specifically that pre-building an empty COOP/PASTURE on
a future production tile moves a future weed-clearing action into otherwise-idle
time.  The official engine does not support that action accounting: an empty
structure prevents the weed roll only while it remains on the tile, and the
structure itself must later be removed with DIG before PLANT/other tile use.

This module proves the lower-bound action result and authenticates the exact
engine semantics it relies on.  It is evidence only; it has no gameplay or
promotion authority.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

OFFICIAL_ENGINE_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
DEFAULT_WEED_CHANCE = 0.005
HORIZONS = (1, 5, 10, 20, 30)


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def _function_source(source: str, name: str) -> str:
    tree = ast.parse(source)
    node = next(
        (item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == name),
        None,
    )
    if node is None:
        raise ValueError(f"missing function: {name}")
    segment = ast.get_source_segment(source, node)
    if not segment:
        raise ValueError(f"cannot recover function source: {name}")
    return segment


def authenticate_engine(engine_path: Path, expected_blob: str = OFFICIAL_ENGINE_BLOB) -> dict:
    data = engine_path.read_bytes()
    blob = git_blob_sha1(data)
    if blob != expected_blob:
        raise ValueError(f"official engine drift: expected {expected_blob}, got {blob}")
    source = data.decode("utf-8")
    spawn = _function_source(source, "_spawn_weeds")
    apply = _function_source(source, "_apply_unit_action")
    eod = _function_source(source, "_end_of_day")

    anchors = {
        "spawn_none_only": 'farm["tiles"][y][x] is None and rng.random() < weed_chance',
        "spawn_assigns_weed": 'farm["tiles"][y][x] = {"kind": "WEED"}',
        "build_coop": 'if op == "BUILD_COOP":',
        "coop_requires_none": 'farm["tiles"][fy][fx] = {"kind": "COOP"}',
        "build_pasture": 'if op == "BUILD_PASTURE":',
        "pasture_requires_none": 'farm["tiles"][fy][fx] = {"kind": "PASTURE"}',
        "dig": 'if op == "DIG":',
        "dig_clears": 'farm["tiles"][fy][fx] = None',
        "default_weed_chance": 'weedSpawnChance", 0.005',
        "shared_rng_call": '_spawn_weeds(farm, board_size, weed_chance, rng)',
    }
    locations = {
        "spawn_none_only": spawn,
        "spawn_assigns_weed": spawn,
        "build_coop": apply,
        "coop_requires_none": apply,
        "build_pasture": apply,
        "pasture_requires_none": apply,
        "dig": apply,
        "dig_clears": apply,
        "default_weed_chance": eod,
        "shared_rng_call": eod,
    }
    missing = [name for name, anchor in anchors.items() if anchor not in locations[name]]
    if missing:
        raise ValueError(f"engine semantic anchors missing: {missing}")

    # BUILD and DIG branches are not monetary transactions: their exact official
    # branches contain no farm money mutation.  This does not make BUILD free in
    # action time; it only means the source agrees it has no cash charge.
    coop_start = apply.index('if op == "BUILD_COOP":')
    pasture_start = apply.index('if op == "BUILD_PASTURE":')
    dig_start = apply.index('if op == "DIG":')
    next_after_pasture = apply.find("\n    if op ==", pasture_start + 1)
    coop_branch = apply[coop_start:pasture_start]
    pasture_branch = apply[pasture_start: next_after_pasture if next_after_pasture != -1 else len(apply)]
    next_after_dig = apply.find("\n    if op ==", dig_start + 1)
    dig_branch = apply[dig_start: next_after_dig if next_after_dig != -1 else len(apply)]
    for label, branch in (("BUILD_COOP", coop_branch), ("BUILD_PASTURE", pasture_branch), ("DIG", dig_branch)):
        if '["money"]' in branch or "['money']" in branch:
            raise ValueError(f"{label} unexpectedly mutates money")

    if "if tile is not None:" not in coop_branch or "if tile is not None:" not in pasture_branch:
        raise ValueError("empty-structure build no longer requires an empty tile")
    if 'and "animal" in tile' not in dig_branch or 'farm["tiles"][fy][fx] = None' not in dig_branch:
        raise ValueError("DIG empty-structure/weed semantics drifted")

    return {
        "engine_blob": blob,
        "default_weed_chance": DEFAULT_WEED_CHANCE,
        "anchors": sorted(anchors),
        "shared_rng_across_player_eod_loop": True,
    }


def weed_present_probability(days: int, chance: float = DEFAULT_WEED_CHANCE) -> float:
    if type(days) is not int or days < 0:
        raise ValueError("days must be a nonnegative integer")
    if not (0.0 <= chance <= 1.0):
        raise ValueError("chance must be in [0,1]")
    return 1.0 - (1.0 - chance) ** days


def action_accounting(days: int, chance: float = DEFAULT_WEED_CHANCE) -> dict:
    """Lower-bound tile-local action accounting for a structure kept until use.

    Baseline leaves the tile empty.  A weed, once spawned, occupies the tile and
    no further weed can spawn there until cleared, so the probability the future
    use needs one DIG is 1-(1-p)^days.

    Shield builds an empty structure earlier and keeps it through the same EOD
    horizon.  That prevents weed rolls on this tile but makes one future DIG
    certain, because PLANT requires an empty tile.  BUILD is one additional
    earlier unit action.  Movement/route opportunity costs are excluded, making
    this maximally favorable to the shield.
    """
    q = weed_present_probability(days, chance)
    return {
        "days": days,
        "chance": chance,
        "baseline_future_dig_expected": q,
        "shield_future_dig_expected": 1.0,
        "shield_earlier_build_actions": 1.0,
        "critical_day_action_penalty": 1.0 - q,
        "total_tile_local_action_penalty": 2.0 - q,
    }


def verdict(chance: float = DEFAULT_WEED_CHANCE, horizons=HORIZONS) -> dict:
    rows = [action_accounting(day, chance) for day in horizons]
    if not all(row["critical_day_action_penalty"] >= 0.0 for row in rows):
        raise AssertionError("shield unexpectedly lowers future DIG burden")
    if not all(row["total_tile_local_action_penalty"] > 0.0 for row in rows):
        raise AssertionError("shield unexpectedly lowers total tile-local actions")
    return {
        "claim": "empty COOP/PASTURE on a future-use tile banks weed-clearing work into idle time",
        "disposition": "FALSIFIED_AS_ACTION_BANK",
        "reason": (
            "Keeping the shield until use makes the future DIG certain; leaving the tile "
            "empty requires that DIG only if a weed has appeared. BUILD adds another "
            "earlier action. Clearing the shield before the final EOD restores weed risk."
        ),
        "rows": rows,
        "limits": [
            "This falsifies empty-structure weed shielding as an action-saving mechanism.",
            "It does not evaluate structures that simultaneously produce animal value.",
            "It ignores movement costs, which can only make a pure shield less favorable.",
            "Shielding changes shared RNG draw consumption, so per-seed other-tile weeds are not a monotone subset.",
        ],
    }


def locate_engine_from_package(package_dir: Path) -> Path:
    # .../cloud-execution-lab/candidates/v4/research/terrain-action-banking
    lab = package_dir.parents[3]
    return lab / "reference" / "engine" / "kaggriculture.py"


def main() -> int:
    here = Path(__file__).resolve().parent
    engine = locate_engine_from_package(here)
    auth = authenticate_engine(engine)
    result = verdict()
    print(json.dumps({"schema": "titan.terrain-bank.falsifier.v1", "authority": auth, **result},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
