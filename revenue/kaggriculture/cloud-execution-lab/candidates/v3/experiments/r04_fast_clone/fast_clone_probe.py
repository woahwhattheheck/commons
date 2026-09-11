#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Measure a behavior-preserving fixed-schema clone for R04 tape actions.

This is intentionally an experiment, not production wiring.  R04 currently calls
``copy.deepcopy(tape[step])`` on every turn before mutating the resulting action.  The 13
Shop Router tapes are JSON-decoded and therefore have a much narrower schema than generic
``deepcopy`` needs to support.  This probe validates the narrow clone against *every* decoded
R04 tape action, checks that all mutable rows are detached from the template, exercises
future-schema fallback isolation, and reports a best-of-N whole-corpus timing for both
implementations.

Run from anywhere in the checkout:

    python revenue/kaggriculture/cloud-execution-lab/candidates/v3/experiments/\
r04_fast_clone/fast_clone_probe.py
"""
from __future__ import annotations

import copy
from pathlib import Path
import statistics
import sys
import time

HERE = Path(__file__).resolve()
V3 = HERE.parents[2]
OVERLAY = V3 / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

import r04_full_router as r04  # noqa: E402


_JSON_SCALAR_TYPES = (str, int, float, bool, type(None))


def _is_json_scalar(value):
    """Accept only immutable JSON scalar leaf values, never containers/subclasses."""
    return type(value) in _JSON_SCALAR_TYPES


def _is_scalar_row(row):
    return isinstance(row, list) and all(_is_json_scalar(value) for value in row)


def is_fast_shape(template):
    """Return whether ``template`` is exactly the shallow-clone-safe R04 JSON action shape."""
    if (not isinstance(template, dict) or len(template) != 3
            or "farmer" not in template or "hands" not in template or "market" not in template):
        return False
    farmer, hands, market = template["farmer"], template["hands"], template["market"]
    return (isinstance(farmer, list)
            and all(_is_json_scalar(value) for value in farmer)
            and isinstance(hands, list)
            and isinstance(market, list)
            and all(_is_scalar_row(row) for row in hands)
            and all(_is_scalar_row(row) for row in market))


def fast_clone_action(template):
    """Clone a fixed-shape action; safely fall back if a future tape changes schema."""
    if not is_fast_shape(template):
        return copy.deepcopy(template)
    return {
        "farmer": list(template["farmer"]),
        "hands": [list(row) for row in template["hands"]],
        "market": [list(row) for row in template["market"]],
    }


def all_actions():
    return [action for tape in r04._INLINE_TAPES for action in tape]


def validate(actions):
    fallback = 0
    for index, template in enumerate(actions):
        if not is_fast_shape(template):
            fallback += 1
        reference = copy.deepcopy(template)
        candidate = fast_clone_action(template)
        if candidate != reference:
            raise AssertionError("clone mismatch at flattened action %d" % index)
        if candidate is template:
            raise AssertionError("top-level alias at flattened action %d" % index)
        for key in ("farmer", "hands", "market"):
            if candidate[key] is template[key]:
                raise AssertionError("%s alias at flattened action %d" % (key, index))
        for key in ("hands", "market"):
            for row_index, row in enumerate(candidate[key]):
                if row is template[key][row_index]:
                    raise AssertionError("%s[%d] alias at flattened action %d" % (key, row_index, index))
    return fallback


def validate_future_schema_fallback():
    """Freeze the review predecessor: nested mutables must use isolated deepcopy fallback."""
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
        if is_fast_shape(template):
            raise AssertionError("%s unexpectedly admitted by fast-shape predicate" % label)
        candidate = fast_clone_action(template)
        if candidate != template:
            raise AssertionError("%s fallback clone mismatch" % label)
        if candidate is template:
            raise AssertionError("%s top-level fallback alias" % label)
        mutate(candidate)
        if template != frozen:
            raise AssertionError("%s nested fallback alias" % label)
    return len(cases)


def timed(fn, actions, repeats=7):
    samples = []
    for _ in range(repeats):
        started = time.perf_counter()
        for action in actions:
            fn(action)
        samples.append(time.perf_counter() - started)
    return min(samples), statistics.median(samples)


def main():
    actions = all_actions()
    expected = 13 * (r04.LAST_STEP + 1)
    if len(actions) != expected:
        raise AssertionError("expected %d decoded actions, found %d" % (expected, len(actions)))
    fallback = validate(actions)
    future_fallback_cases = validate_future_schema_fallback()
    deep_best, deep_median = timed(copy.deepcopy, actions)
    fast_best, fast_median = timed(fast_clone_action, actions)
    best_speedup = deep_best / fast_best if fast_best else float("inf")
    median_speedup = deep_median / fast_median if fast_median else float("inf")
    print("R04 FAST CLONE PROBE PASS")
    print("actions=%d fallback_shapes=%d future_fallback_cases=%d" %
          (len(actions), fallback, future_fallback_cases))
    print("deepcopy_best_s=%.6f fast_best_s=%.6f best_speedup=%.2fx" %
          (deep_best, fast_best, best_speedup))
    print("deepcopy_median_s=%.6f fast_median_s=%.6f median_speedup=%.2fx" %
          (deep_median, fast_median, median_speedup))


if __name__ == "__main__":
    main()
