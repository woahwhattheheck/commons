#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve()
V3 = HERE.parents[2]
OVERLAY = V3 / "overlay"
for path in (HERE.parent, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import b8_budget_guard as b8  # noqa: E402
import r04_full_router as r04  # noqa: E402


def test_fixed_cost_exact_rows():
    actions = [
        {"market": [["SELL", "MILK", 3], ["BUY_LAND"]]},
        {"market": [["BUY_ANIMAL", "SHEEP", 2], ["BUY_SEED", "CARROT", 4]]},
    ]
    assert b8._fixed_cost_of_future_actions(actions) == 4000 + 2 * 500 + 4 * 20


def test_dynamic_future_cost_fails_open():
    assert b8._fixed_cost_of_future_actions([{"market": [["BUY_PRODUCT", "WHEAT", 1]]}]) is None
    assert b8._fixed_cost_of_future_actions([{"market": [["HIRE"]]}]) is None


def test_type_confusion_fails_open():
    assert b8._fixed_cost_of_future_actions([{"market": [["BUY_ANIMAL", "SHEEP", True]]}]) is None
    assert b8._fixed_cost_of_future_actions([{"market": [["BUY_SEED", "WHEAT", 1.0]]}]) is None
    assert b8._fixed_cost_of_future_actions([{"market": [["BUY_LAND", 1]]}]) is None


def test_guard_blocks_only_when_parent_would_invest():
    old_native = r04._v219_native_day
    parent_report = {"calls": 0}
    try:
        r04._v219_native_day = lambda native, day: [
            {"market": []},
            {"market": [["BUY_LAND"]]},
        ]
        b8.reset_report()
        obs = {"step": 0, "player": 0, "farms": [{"money": 4050}]}
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        state = {}

        def original(local_obs, local_action, local_state, native):
            parent_report["calls"] += 1
            local_state["seen"] = True
            if local_obs["farms"][0]["money"] >= 100:
                changed = dict(local_action)
                changed["market"] = [["BUY_SEED", "WHEAT", 1]]
                return changed
            return local_action

        result = b8._guard_request("v219", original, parent_report, obs, action, state, object())
        assert result == action
        assert state.get("seen") is True
        # Shadow telemetry was restored; only the authoritative guarded call remains.
        assert parent_report["calls"] == 1
        assert b8.REPORT["parent_would_invest"] == 1
        assert b8.REPORT["activations"] == 1
        assert b8.REPORT["v219_activations"] == 1
        assert b8.REPORT["reserved_cash"] == 4000
        assert b8.REPORT["trace"][0]["money"] == 4050
    finally:
        r04._v219_native_day = old_native


def test_guard_preserves_parent_when_reserve_is_affordable():
    old_native = r04._v219_native_day
    parent_report = {"calls": 0}
    try:
        r04._v219_native_day = lambda native, day: [
            {"market": []},
            {"market": [["BUY_SEED", "WHEAT", 2]]},
        ]
        b8.reset_report()
        obs = {"step": 0, "player": 0, "farms": [{"money": 1000}]}
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        state = {}

        def original(local_obs, local_action, local_state, native):
            parent_report["calls"] += 1
            if local_obs["farms"][0]["money"] >= 100:
                changed = dict(local_action)
                changed["market"] = [["BUY_SEED", "WHEAT", 1]]
                return changed
            return local_action

        result = b8._guard_request("v233", original, parent_report, obs, action, state, object())
        assert result["market"] == [["BUY_SEED", "WHEAT", 1]]
        assert parent_report["calls"] == 1
        assert b8.REPORT["activations"] == 0
    finally:
        r04._v219_native_day = old_native


def test_incomplete_bound_is_parent_exact_and_single_call():
    old_native = r04._v219_native_day
    calls = {"n": 0}
    try:
        r04._v219_native_day = lambda native, day: [
            {"market": []},
            {"market": [["BUY_PRODUCT", "WHEAT", 1]]},
        ]
        b8.reset_report()
        obs = {"step": 0, "player": 0, "farms": [{"money": 1}]}
        action = {"farmer": ["PASS"], "hands": [], "market": []}

        def original(local_obs, local_action, local_state, native):
            calls["n"] += 1
            return local_action

        result = b8._guard_request("v219", original, {}, obs, action, {}, object())
        assert result is action
        assert calls["n"] == 1
        assert b8.REPORT["proof_complete"] == 0
    finally:
        r04._v219_native_day = old_native


def test_install_off_restores_parent_requests():
    b8.install(None, enabled=False, horizon=8, opening=0, row_order=True,
               evening_flush=True, sale_fertilizer=True, cattle_early=True)
    assert r04._v219_request is b8._ORIGINAL_V219_REQUEST
    assert r04._v233_request is b8._ORIGINAL_V233_REQUEST
    b8.install(None, enabled=True, horizon=8, opening=0, row_order=True,
               evening_flush=True, sale_fertilizer=True, cattle_early=True)
    assert r04._v219_request is b8.guarded_v219_request
    assert r04._v233_request is b8.guarded_v233_request
    b8.install(None, enabled=False, horizon=8, opening=0, row_order=True,
               evening_flush=True, sale_fertilizer=True, cattle_early=True)


def main():
    tests = [name for name, value in globals().items() if name.startswith("test_") and callable(value)]
    for name in sorted(tests):
        globals()[name]()
        print("PASS", name)
    print(f"PASS {len(tests)} B8 focused contracts")


if __name__ == "__main__":
    main()
