#!/usr/bin/env python3
"""Source-bound census for provably removable main-farmer motion loops in TITAN V4 tapes.

This module is research-only. It does not mutate tapes or runtime policy.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

TURNS_PER_DAY = 24
ROUTE_STEP = 144
FINAL_PLAN_STEP = 648
LAST_STEP = 718
TAPE_COUNT = 13
TAPE_STEPS = LAST_STEP + 1
BOARD_SIZE = 10

EXPECTED_ENGINE_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
EXPECTED_TAPES_BLOB = "a43289b9cc5e34a2481fddf652762a7d92f427ef"
EXPECTED_ROUTER_BLOB = "a3e2fe87c717d128e43c9b65bae2265f40d1d76d"

MOVES = {
    "NORTH": (0, -1),
    "SOUTH": (0, 1),
    "EAST": (1, 0),
    "WEST": (-1, 0),
}
PASSIVE = frozenset({"PASS", *MOVES})

HERE = Path(__file__).resolve()
V4_ROOT = HERE.parents[2]
TAPES_PATH = V4_ROOT / "donor" / "overlay" / "r01_tapes.py"
ROUTER_PATH = V4_ROOT / "donor" / "overlay" / "r04_full_router.py"
ENGINE_PATH = V4_ROOT.parent.parent / "reference" / "engine" / "kaggriculture.py"


class MotionCensusError(RuntimeError):
    pass


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _require_markers(text: str, markers: tuple[str, ...], label: str) -> None:
    missing = [marker for marker in markers if marker not in text]
    if missing:
        raise MotionCensusError(f"{label} semantics drifted; missing {missing!r}")


def verify_sources(
    *,
    engine_path: Path = ENGINE_PATH,
    tapes_path: Path = TAPES_PATH,
    router_path: Path = ROUTER_PATH,
) -> dict[str, str]:
    actual = {
        "engine_blob": git_blob(engine_path),
        "r01_tapes_blob": git_blob(tapes_path),
        "r04_full_router_blob": git_blob(router_path),
    }
    expected = {
        "engine_blob": EXPECTED_ENGINE_BLOB,
        "r01_tapes_blob": EXPECTED_TAPES_BLOB,
        "r04_full_router_blob": EXPECTED_ROUTER_BLOB,
    }
    for key, want in expected.items():
        if actual[key] != want:
            raise MotionCensusError(
                f"{key} drift: expected {want}, got {actual[key]}"
            )

    engine = engine_path.read_text(encoding="utf-8")
    _require_markers(
        engine,
        (
            'FARMER_MOVES = {',
            'if op in FARMER_MOVES:',
            '_set_farmer_position(farm, idx, (nx, ny))',
            'if op == "HIRE":',
            '_do_hire(farms[player_id], privates[player_id], board_size, hire_mult)',
            'farm["hands"].append(_spawn_hand(farm, board_size))',
            'farm["farmer"] = list(_default_spawn(board_size))',
            'farm["hands"] = []',
            '_apply_unit_action(obs0.farms[i], s.observation.private, 0, _allowed(farmer_action),',
            '_process_market(state, env)',
        ),
        "engine",
    )
    router = router_path.read_text(encoding="utf-8")
    _require_markers(
        router,
        (
            "ROUTE_STEP = 144",
            "FINAL_PLAN_STEP = 648",
            "LAST_STEP = 718",
            "state.plan = SHOP_PLANS.get(tuple(shops[:2]), 0)",
            "state.plan = 2",
            "tape = self.tapes[state.plan]",
            "action = copy.deepcopy(tape[step])",
        ),
        "router",
    )
    return actual


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location("_titan_v4_motion_tapes", path)
    if spec is None or spec.loader is None:
        raise MotionCensusError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_tapes(path: Path = TAPES_PATH) -> list[list[dict[str, Any]]]:
    tapes = _load_module(path).load_tapes()
    if len(tapes) != TAPE_COUNT or any(len(tape) != TAPE_STEPS for tape in tapes):
        raise MotionCensusError(
            f"expected {TAPE_COUNT}x{TAPE_STEPS} tapes, got "
            f"{len(tapes)} / {[len(t) for t in tapes[:3]]}"
        )
    return tapes


def effective_route(tapes: list[list[dict[str, Any]]], plan: int) -> list[dict[str, Any]]:
    if not 0 <= plan < TAPE_COUNT:
        raise MotionCensusError(f"plan out of range: {plan}")
    if len(tapes) != TAPE_COUNT or any(len(tape) != TAPE_STEPS for tape in tapes):
        raise MotionCensusError("malformed tape bank")
    return (
        tapes[0][:ROUTE_STEP]
        + tapes[plan][ROUTE_STEP:FINAL_PLAN_STEP]
        + tapes[2][FINAL_PLAN_STEP:]
    )


def _default_spawn(board_size: int = BOARD_SIZE) -> tuple[int, int]:
    half = board_size // 2
    candidates = (
        (half - 1, half - 1),
        (half, half - 1),
        (half - 1, half),
        (half, half),
    )
    for x, y in candidates:
        if x < half and y < half:
            return x, y
    return 0, 0


def _farmer_row(action: Any) -> list[Any]:
    if not isinstance(action, dict):
        return ["PASS"]
    row = action.get("farmer") or ["PASS"]
    return row if isinstance(row, list) and row else ["PASS"]


def _op(action: Any) -> str:
    row = _farmer_row(action)
    return str(row[0]) if row else "PASS"


def _has_hire(action: Any) -> bool:
    if not isinstance(action, dict):
        return False
    market = action.get("market") or []
    if not isinstance(market, list):
        return False
    return any(
        isinstance(row, list) and row and row[0] == "HIRE"
        for row in market
    )


def _move(pos: tuple[int, int], op: str, board_size: int) -> tuple[tuple[int, int], bool]:
    delta = MOVES.get(op)
    if delta is None:
        return pos, False
    nx, ny = pos[0] + delta[0], pos[1] + delta[1]
    if not (0 <= nx < board_size and 0 <= ny < board_size):
        return pos, False
    return (nx, ny), True


def census_route(
    route: list[dict[str, Any]],
    *,
    plan: int = -1,
    board_size: int = BOARD_SIZE,
    turns_per_day: int = TURNS_PER_DAY,
) -> dict[str, Any]:
    """Find non-overlapping source-theorem-safe main-farmer movement loops.

    A loop is admitted only inside one day, across unit rows limited to MOVE/PASS,
    with no HIRE market row in the interval, and with exact simulated farmer
    position returning to the same tile. Movement is the only unit side effect in
    such an interval; excluding HIRE removes the one market operation whose spawn
    result consumes farmer/hand positions.
    """
    if board_size <= 0 or turns_per_day <= 0:
        raise MotionCensusError("positive board_size/turns_per_day required")

    pos = _default_spawn(board_size)
    seen: dict[tuple[int, int], int] = {pos: 0}
    move_prefix = [0]
    intervals: list[dict[str, Any]] = []
    boundary_noops: list[int] = []
    movement_rows = 0
    hire_rows = 0

    for step, action in enumerate(route):
        if step > 0 and step % turns_per_day == 0:
            pos = _default_spawn(board_size)
            seen = {pos: step}

        op = _op(action)
        has_hire = _has_hire(action)
        if has_hire:
            hire_rows += 1

        after, executed = _move(pos, op, board_size)
        if op in MOVES:
            movement_rows += 1
            if not executed:
                boundary_noops.append(step)
        pos = after
        move_prefix.append(move_prefix[-1] + int(executed))

        if op not in PASSIVE or has_hire:
            seen = {pos: step + 1}
            continue

        prior_boundary = seen.get(pos)
        if prior_boundary is not None:
            executed_moves = move_prefix[step + 1] - move_prefix[prior_boundary]
            if executed_moves > 0:
                interval_moves = [
                    idx
                    for idx in range(prior_boundary, step + 1)
                    if _op(route[idx]) in MOVES
                ]
                intervals.append(
                    {
                        "start_step": prior_boundary,
                        "end_step": step,
                        "day": step // turns_per_day,
                        "position": [pos[0], pos[1]],
                        "movement_rows": interval_moves,
                        "movement_row_count": len(interval_moves),
                        "executed_move_count": executed_moves,
                    }
                )
                seen = {pos: step + 1}
                continue

        seen[pos] = step + 1

    loop_rows = sorted(
        {idx for interval in intervals for idx in interval["movement_rows"]}
    )
    all_safe = sorted(set(boundary_noops) | set(loop_rows))
    return {
        "plan": plan,
        "steps": len(route),
        "movement_rows": movement_rows,
        "hire_market_rows": hire_rows,
        "boundary_noop_rows": boundary_noops,
        "closed_hire_free_motion_loops": intervals,
        "closed_loop_count": len(intervals),
        "closed_loop_movement_rows": loop_rows,
        "provably_pass_equivalent_movement_rows": all_safe,
        "provably_pass_equivalent_count": len(all_safe),
    }


def build_report(tapes: list[list[dict[str, Any]]], sources: dict[str, str]) -> dict[str, Any]:
    routes = [
        census_route(effective_route(tapes, plan), plan=plan)
        for plan in range(TAPE_COUNT)
    ]
    return {
        "schema": "titan.v4.route-motion-census.v1",
        "status": "SOURCE_BOUND_RESEARCH_ONLY",
        "sources": sources,
        "theorem": {
            "scope": "main farmer actor 0 only; fixed effective routes",
            "safe_rewrite": "listed movement rows are PASS-equivalent under pinned engine/router semantics",
            "guards": [
                "same day only",
                "no substantive main-farmer unit action inside closed loop",
                "no HIRE market row inside closed loop",
                "exact actor-0 position returns to loop start",
                "out-of-bounds movement is already a unit no-op",
            ],
        },
        "route_splice": {
            "opening": [0, ROUTE_STEP - 1, 0],
            "midgame": [ROUTE_STEP, FINAL_PLAN_STEP - 1, "plan"],
            "endgame": [FINAL_PLAN_STEP, LAST_STEP, 2],
        },
        "routes": routes,
        "totals": {
            "movement_rows": sum(r["movement_rows"] for r in routes),
            "closed_loop_count": sum(r["closed_loop_count"] for r in routes),
            "provably_pass_equivalent_count": sum(
                r["provably_pass_equivalent_count"] for r in routes
            ),
            "routes_with_safe_rows": sum(
                bool(r["provably_pass_equivalent_count"]) for r in routes
            ),
        },
        "not_claimed": [
            "hand/worker motion optimality",
            "natural current-native incidence after all runtime repairs",
            "economic uplift",
            "runtime activation",
            "default promotion",
            "archive or Kaggle mutation",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    sources = verify_sources()
    report = build_report(load_tapes(), sources)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
