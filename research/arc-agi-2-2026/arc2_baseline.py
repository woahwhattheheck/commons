#!/usr/bin/env python3
"""Deterministic ARC-AGI-2 baseline and Kaggle submission packager.

The solver learns a small symbolic hypothesis from each task's training pairs.
A hypothesis is a fixed geometric transform plus one global color remapping.
It deliberately uses only task-local examples and the Python standard library.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Sequence, Tuple

Grid = List[List[int]]
Task = Mapping[str, Sequence[Mapping[str, Grid]]]
Transform = Callable[[Grid], Grid]


def validate_grid(grid: object) -> Grid:
    if not isinstance(grid, list) or not grid or not all(isinstance(r, list) and r for r in grid):
        raise ValueError("grid must be a non-empty list of non-empty rows")
    width = len(grid[0])
    if len(grid) > 30 or width > 30:
        raise ValueError("ARC grids must be at most 30x30")
    out: Grid = []
    for row in grid:
        if len(row) != width:
            raise ValueError("grid rows must have equal length")
        checked: List[int] = []
        for value in row:
            if type(value) is not int or not 0 <= value <= 9:
                raise ValueError("ARC cell values must be integers in [0, 9]")
            checked.append(value)
        out.append(checked)
    return out


def validate_task(task: object, require_train_outputs: bool = True) -> Mapping[str, Sequence[Mapping[str, Grid]]]:
    if not isinstance(task, dict):
        raise ValueError("task must be an object")
    train = task.get("train")
    test = task.get("test")
    if not isinstance(train, list) or not train:
        raise ValueError("task.train must be a non-empty list")
    if not isinstance(test, list) or not test:
        raise ValueError("task.test must be a non-empty list")
    for split_name, pairs in (("train", train), ("test", test)):
        for pair in pairs:
            if not isinstance(pair, dict) or "input" not in pair:
                raise ValueError(f"{split_name} pair must contain input")
            validate_grid(pair["input"])
            if split_name == "train" and require_train_outputs:
                if "output" not in pair:
                    raise ValueError("train pair must contain output")
                validate_grid(pair["output"])
    return task


def copy_grid(g: Grid) -> Grid:
    return [row[:] for row in g]


def rot90(g: Grid) -> Grid:
    return [list(row) for row in zip(*g[::-1])]


def rot180(g: Grid) -> Grid:
    return [row[::-1] for row in g[::-1]]


def rot270(g: Grid) -> Grid:
    return [list(row) for row in zip(*g)][::-1]


def flip_h(g: Grid) -> Grid:
    return [row[::-1] for row in g]


def flip_v(g: Grid) -> Grid:
    return [row[:] for row in g[::-1]]


def transpose(g: Grid) -> Grid:
    return [list(row) for row in zip(*g)]


def anti_transpose(g: Grid) -> Grid:
    return rot180(transpose(g))


def crop_nonzero(g: Grid) -> Grid:
    coords = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v != 0]
    if not coords:
        return copy_grid(g)
    r0, r1 = min(r for r, _ in coords), max(r for r, _ in coords)
    c0, c1 = min(c for _, c in coords), max(c for _, c in coords)
    return [row[c0 : c1 + 1] for row in g[r0 : r1 + 1]]


def upscale2(g: Grid) -> Grid:
    out: Grid = []
    for row in g:
        expanded = [v for v in row for _ in range(2)]
        out.append(expanded[:])
        out.append(expanded[:])
    return out


def repeat_rows2(g: Grid) -> Grid:
    return [row[:] for row in g for _ in range(2)]


def repeat_cols2(g: Grid) -> Grid:
    return [[v for v in row for _ in range(2)] for row in g]


def tile2x2(g: Grid) -> Grid:
    doubled_rows = [row + row for row in g]
    return doubled_rows + [row[:] for row in doubled_rows]


def mirror_quadrants(g: Grid) -> Grid:
    """Mirror the input across its right and bottom edges, doubling both axes."""
    wide = [row + row[::-1] for row in g]
    return wide + [row[:] for row in wide[::-1]]


def complete_latin_square(g: Grid) -> Grid:
    """Fill 0-valued blanks when row/column constraints force a Latin square.

    The transform is deliberately conservative: it only acts on an n×n grid
    containing exactly n non-zero symbols and returns the original grid unless
    every blank can be resolved by singleton row/column intersections.
    """
    n = len(g)
    if n != len(g[0]) or not 2 <= n <= 9:
        return copy_grid(g)
    symbols = {v for row in g for v in row if v != 0}
    if len(symbols) != n:
        return copy_grid(g)
    out = copy_grid(g)
    if not any(v == 0 for row in out for v in row):
        return out

    while True:
        progress = False
        for r in range(n):
            for c in range(n):
                if out[r][c] != 0:
                    continue
                row_used = {v for v in out[r] if v != 0}
                col_used = {out[rr][c] for rr in range(n) if out[rr][c] != 0}
                candidates = symbols - row_used - col_used
                if len(candidates) == 1:
                    out[r][c] = next(iter(candidates))
                    progress = True
        if not progress:
            break

    if any(v == 0 for row in out for v in row):
        return copy_grid(g)
    if any(set(row) != symbols for row in out):
        return copy_grid(g)
    if any({out[r][c] for r in range(n)} != symbols for c in range(n)):
        return copy_grid(g)
    return out


TRANSFORMS: Tuple[Tuple[str, Transform], ...] = (
    ("identity", copy_grid),
    ("rot90", rot90),
    ("rot180", rot180),
    ("rot270", rot270),
    ("flip_h", flip_h),
    ("flip_v", flip_v),
    ("transpose", transpose),
    ("anti_transpose", anti_transpose),
    ("complete_latin_square", complete_latin_square),
    ("mirror_quadrants", mirror_quadrants),
    ("crop_nonzero", crop_nonzero),
    ("upscale2", upscale2),
    ("repeat_rows2", repeat_rows2),
    ("repeat_cols2", repeat_cols2),
    ("tile2x2", tile2x2),
)


def same_shape(a: Grid, b: Grid) -> bool:
    return len(a) == len(b) and len(a[0]) == len(b[0])


def infer_color_map(source: Grid, target: Grid, existing: Mapping[int, int] | None = None) -> Dict[int, int] | None:
    if not same_shape(source, target):
        return None
    mapping: Dict[int, int] = dict(existing or {})
    for src_row, dst_row in zip(source, target):
        for src, dst in zip(src_row, dst_row):
            if src in mapping and mapping[src] != dst:
                return None
            mapping[src] = dst
    return mapping


def apply_color_map(grid: Grid, mapping: Mapping[int, int]) -> Grid:
    return [[mapping.get(v, v) for v in row] for row in grid]


@dataclass(frozen=True)
class Hypothesis:
    transform_name: str
    color_map_items: Tuple[Tuple[int, int], ...]

    @property
    def color_map(self) -> Dict[int, int]:
        return dict(self.color_map_items)

    def apply(self, grid: Grid) -> Grid:
        transform = dict(TRANSFORMS)[self.transform_name]
        return apply_color_map(transform(grid), self.color_map)


def fit_hypotheses(task: Task) -> List[Hypothesis]:
    validate_task(task)
    fits: List[Hypothesis] = []
    for name, transform in TRANSFORMS:
        mapping: Dict[int, int] = {}
        ok = True
        for pair in task["train"]:
            source = transform(validate_grid(pair["input"]))
            target = validate_grid(pair["output"])
            merged = infer_color_map(source, target, mapping)
            if merged is None:
                ok = False
                break
            mapping = merged
        if ok:
            fits.append(Hypothesis(name, tuple(sorted(mapping.items()))))
    transform_rank = {name: i for i, (name, _) in enumerate(TRANSFORMS)}
    fits.sort(
        key=lambda h: (
            sum(1 for src, dst in h.color_map_items if src != dst),
            transform_rank[h.transform_name],
        )
    )
    return fits


def distinct_predictions(task: Task, test_grid: Grid, limit: int = 2) -> List[Grid]:
    predictions: List[Grid] = []
    seen = set()
    for hypothesis in fit_hypotheses(task):
        pred = hypothesis.apply(test_grid)
        key = json.dumps(pred, separators=(",", ":"))
        if key not in seen:
            predictions.append(pred)
            seen.add(key)
            if len(predictions) >= limit:
                return predictions

    # Conservative deterministic fallbacks ensure exactly two attempts.
    for fallback in (copy_grid(test_grid), rot180(test_grid)):
        key = json.dumps(fallback, separators=(",", ":"))
        if key not in seen:
            predictions.append(fallback)
            seen.add(key)
        if len(predictions) >= limit:
            break
    while len(predictions) < limit:
        predictions.append(copy_grid(test_grid))
    return predictions[:limit]


def solve_task(task: Task) -> List[Dict[str, Grid]]:
    validate_task(task)
    outputs: List[Dict[str, Grid]] = []
    for pair in task["test"]:
        test_grid = validate_grid(pair["input"])
        p1, p2 = distinct_predictions(task, test_grid, 2)
        outputs.append({"attempt_1": p1, "attempt_2": p2})
    return outputs


def build_submission(challenges: Mapping[str, Task]) -> Dict[str, List[Dict[str, Grid]]]:
    if not isinstance(challenges, dict) or not challenges:
        raise ValueError("challenge file must map task ids to tasks")
    submission: Dict[str, List[Dict[str, Grid]]] = {}
    for task_id, task in challenges.items():
        if not isinstance(task_id, str) or not task_id:
            raise ValueError("task ids must be non-empty strings")
        submission[task_id] = solve_task(task)
    return submission


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("challenges", type=Path, help="ARC challenge JSON")
    parser.add_argument("--output", type=Path, default=Path("submission.json"))
    args = parser.parse_args(argv)

    with args.challenges.open("r", encoding="utf-8") as fh:
        challenges = json.load(fh)
    submission = build_submission(challenges)
    args.output.write_text(json.dumps(submission, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {len(submission)} tasks to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
