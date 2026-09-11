#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Validate the R04 fast-clone production patch against the frozen V3.1 router.

This gate intentionally applies production.patch only inside the ephemeral CI checkout.
The committed V3.1 overlay remains unchanged until reviewers choose to consume the proven
patch. The clone predicate is carried from the hardened R04 experiment (#12361/#12383).
"""
from __future__ import annotations

import copy
import importlib
import inspect
from pathlib import Path
import statistics
import subprocess
import sys
import time

HERE = Path(__file__).resolve()
V3 = HERE.parents[2]
OVERLAY = V3 / "overlay"
SOURCE = OVERLAY / "r04_full_router.py"
PATCH = HERE.with_name("production.patch")
EXPECTED_SOURCE_BLOB = "21c4f1db0298f8955b1f5ad366bd780a89cad206"
EXPECTED_ACTIONS = 13 * 719
MIN_MEDIAN_SPEEDUP = 1.50


def repo_root() -> Path:
    for parent in (HERE.parent, *HERE.parents):
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("repository root not found")


ROOT = repo_root()


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def validate_future_schema_fallback(r04) -> int:
    cases = [
        (
            "farmer_nested_list",
            {"farmer": ["MOVE", ["NORTH"]], "hands": [], "market": []},
            lambda action: action["farmer"][1].append("SOUTH"),
        ),
        (
            "hands_nested_dict",
            {"farmer": ["WAIT"], "hands": [["CARE", 0, {"meta": ["x"]}]], "market": []},
            lambda action: action["hands"][0][2]["meta"].append("y"),
        ),
        (
            "market_tuple_with_mutable",
            {"farmer": ["WAIT"], "hands": [], "market": [["SELL", "MILK", (["x"],)]]},
            lambda action: action["market"][0][2][0].append("y"),
        ),
        (
            "market_nested_set",
            {"farmer": ["WAIT"], "hands": [], "market": [["SELL", "MILK", {"x"}]]},
            lambda action: action["market"][0][2].add("y"),
        ),
    ]
    for label, template, mutate in cases:
        frozen = copy.deepcopy(template)
        if r04._r04_is_fast_tape_action(template):
            raise AssertionError(f"{label} unexpectedly admitted by fast-shape predicate")
        candidate = r04._r04_clone_tape_action(template)
        if candidate != template or candidate is template:
            raise AssertionError(f"{label} deepcopy fallback mismatch")
        mutate(candidate)
        if template != frozen:
            raise AssertionError(f"{label} nested fallback alias")
    return len(cases)


def timed(fn, actions, repeats: int = 7) -> tuple[float, float]:
    samples = []
    for _ in range(repeats):
        started = time.perf_counter()
        for action in actions:
            fn(action)
        samples.append(time.perf_counter() - started)
    return min(samples), statistics.median(samples)


def main() -> None:
    observed_blob = run("git", "hash-object", str(SOURCE.relative_to(ROOT))).stdout.strip()
    if observed_blob != EXPECTED_SOURCE_BLOB:
        raise AssertionError(
            f"wrong frozen R04 source blob: expected {EXPECTED_SOURCE_BLOB}, got {observed_blob}"
        )

    run("git", "apply", "--check", str(PATCH.relative_to(ROOT)))
    run("git", "apply", str(PATCH.relative_to(ROOT)))
    run(sys.executable, "-m", "py_compile", str(SOURCE.relative_to(ROOT)))

    if str(OVERLAY) not in sys.path:
        sys.path.insert(0, str(OVERLAY))
    importlib.invalidate_caches()
    r04 = importlib.import_module("r04_full_router")

    policy_source = inspect.getsource(r04.Policy.act)
    if "_r04_clone_tape_action(tape[step])" not in policy_source:
        raise AssertionError("Policy.act is not wired to the fast tape clone")

    actions = [action for tape in r04._INLINE_TAPES for action in tape]
    if len(actions) != EXPECTED_ACTIONS:
        raise AssertionError(f"expected {EXPECTED_ACTIONS} tape actions, found {len(actions)}")

    fallback_shapes = 0
    for index, template in enumerate(actions):
        if not r04._r04_is_fast_tape_action(template):
            fallback_shapes += 1
        reference = copy.deepcopy(template)
        candidate = r04._r04_clone_tape_action(template)
        if candidate != reference:
            raise AssertionError(f"clone mismatch at flattened action {index}")
        if candidate is template:
            raise AssertionError(f"top-level alias at flattened action {index}")
        for key in ("farmer", "hands", "market"):
            if candidate[key] is template[key]:
                raise AssertionError(f"{key} alias at flattened action {index}")
        for key in ("hands", "market"):
            for row_index, row in enumerate(candidate[key]):
                if row is template[key][row_index]:
                    raise AssertionError(f"{key}[{row_index}] alias at flattened action {index}")

    if fallback_shapes != 0:
        raise AssertionError(f"frozen corpus unexpectedly needs {fallback_shapes} fallbacks")

    future_fallback_cases = validate_future_schema_fallback(r04)

    deep_best, deep_median = timed(copy.deepcopy, actions)
    fast_best, fast_median = timed(r04._r04_clone_tape_action, actions)
    best_speedup = deep_best / fast_best if fast_best else float("inf")
    median_speedup = deep_median / fast_median if fast_median else float("inf")
    if median_speedup < MIN_MEDIAN_SPEEDUP:
        raise AssertionError(
            f"median speedup {median_speedup:.2f}x below {MIN_MEDIAN_SPEEDUP:.2f}x gate"
        )

    print("R04 FAST CLONE PRODUCTION PATCH PASS")
    print(
        f"actions={len(actions)} fallback_shapes={fallback_shapes} "
        f"future_fallback_cases={future_fallback_cases}"
    )
    print(
        f"deepcopy_best_s={deep_best:.6f} fast_best_s={fast_best:.6f} "
        f"best_speedup={best_speedup:.2f}x"
    )
    print(
        f"deepcopy_median_s={deep_median:.6f} fast_median_s={fast_median:.6f} "
        f"median_speedup={median_speedup:.2f}x"
    )


if __name__ == "__main__":
    main()
