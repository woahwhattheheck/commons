#!/usr/bin/env python3
"""Source-bound BUY_LAND/LOCKED-movement phase oracle for TITAN V4."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path

ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
HERE = Path(__file__).resolve().parent
LAB = HERE.parents[3] if len(HERE.parents) > 3 else HERE
DEFAULT_ENGINE = LAB / "reference" / "engine" / "kaggriculture.py"

def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def _function(source: str, name: str) -> str:
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    hits = []
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            hits.append(source[offsets[node.lineno - 1]:offsets[node.end_lineno]])
    if len(hits) != 1:
        raise ValueError(f"expected exactly one top-level {name}, got {len(hits)}")
    return hits[0]

def _ordered(part: str, *needles: str) -> bool:
    positions = [part.find(n) for n in needles]
    return all(p >= 0 for p in positions) and positions == sorted(positions)

def analyze_text(source: str) -> dict:
    unit = _function(source, "_apply_unit_action")
    buy = _function(source, "_do_buy_land")
    market = _function(source, "_process_market")
    interp = _function(source, "interpreter")

    checks = {
        "locked_move_precedes_tile_guard": _ordered(
            unit,
            "if op in FARMER_MOVES:",
            "_set_farmer_position",
            'tile = farm["tiles"][fy][fx]',
        ),
        "locked_move_is_explicitly_legal":
            "Movement onto LOCKED tiles is allowed" in unit,
        "buy_land_cash_guard_precedes_unlock": _ordered(
            buy,
            'if farm["money"] < cost:',
            "return",
            'farm["unlocked_quadrants"].append(quadrant)',
            'farm["tiles"][y][x] = None',
        ),
        "buy_land_market_dispatch": _ordered(
            market,
            'elif op == "BUY_LAND":',
            "_do_buy_land",
            "order_states[player_id] = None",
        ),
        "unit_phase_precedes_market_phase": _ordered(
            interp,
            "_apply_unit_action",
            "_process_market",
        ),
    }
    failed = [k for k, v in checks.items() if not v]
    if failed:
        raise ValueError("source theorem failed: " + ", ".join(failed))
    return {
        "schema": "titan-v4-locked-land-preposition/v1",
        "checks": checks,
        "theorem": {
            "precondition": (
                "actor is in-bounds and can MOVE into the next still-LOCKED quadrant; "
                "the same callback carries an affordable BUY_LAND for that next quadrant"
            ),
            "phase_order": ["unit MOVE", "market BUY_LAND", "tile unlock"],
            "postcondition": (
                "actor position is preserved inside the now-unlocked purchased quadrant "
                "at callback end"
            ),
            "next_callback": (
                "tile operations at that position are no longer rejected merely because "
                "the tile was LOCKED before purchase"
            ),
            "failed_purchase_control": (
                "cash guard returns before unlock, so pre-positioning alone does not grant "
                "tile-operation access"
            ),
            "timing_consequence": (
                "movement completed before purchase need not be repeated after purchase; "
                "a one-edge witness advances earliest productive tile work by one callback "
                "relative to post-purchase movement"
            ),
        },
        "scope": "RESEARCH_ONLY_NO_POLICY_PROMOTION",
    }

def analyze_engine(path: Path = DEFAULT_ENGINE) -> dict:
    data = path.read_bytes()
    observed = git_blob(data)
    if observed != ENGINE_GIT_BLOB:
        raise SystemExit(f"engine drift: {observed} != {ENGINE_GIT_BLOB}")
    result = analyze_text(data.decode("utf-8"))
    result["engine_git_blob"] = observed
    result["engine_path"] = str(path)
    return result

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", type=Path, default=DEFAULT_ENGINE)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    result = analyze_engine(args.engine)
    text = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.out:
        args.out.write_text(text)
    else:
        print(text, end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
