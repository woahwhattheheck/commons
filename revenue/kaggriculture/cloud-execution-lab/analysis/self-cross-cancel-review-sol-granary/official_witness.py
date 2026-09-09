# SPDX-License-Identifier: Apache-2.0
"""Exact preserved-engine theorem witness for same-turn WHEAT self-crosses.

This is a review artifact, not a gameplay candidate.  It proves that deleting an
own SELL and later BUY_PRODUCT can have opposite cash effects under two legal
intervening rival actions even when all terminal non-money state is identical.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ENGINE_PATH = ROOT / "reference" / "engine" / "kaggriculture.py"
EXPECTED_ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"


def _git_blob(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()


def _load_engine():
    raw = ENGINE_PATH.read_bytes()
    blob = _git_blob(raw)
    if blob != EXPECTED_ENGINE_GIT_BLOB:
        raise RuntimeError(
            f"official engine drift: expected {EXPECTED_ENGINE_GIT_BLOB}, got {blob}"
        )
    spec = importlib.util.spec_from_file_location("_sol_granary_self_cross_engine", ENGINE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {ENGINE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, raw, blob


def _strict_money(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("money must be a real number")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("money must be finite")
    return value


def _execute(
    engine,
    markets: list[list[list[Any]]],
    *,
    cash: tuple[float, float] = (1000.0, 1000.0),
    wheat: tuple[int, int] = (1, 0),
    inventory: int = 10_000,
) -> dict[str, Any]:
    if len(markets) != 2 or len(cash) != 2 or len(wheat) != 2:
        raise ValueError("exactly two players are required")
    farms = [engine._new_farm(10, _strict_money(cash[player])) for player in range(2)]
    privates = [engine._new_private() for _ in range(2)]
    for player in range(2):
        if isinstance(wheat[player], bool) or not isinstance(wheat[player], int) or wheat[player] < 0:
            raise ValueError("WHEAT stock must be a nonnegative integer")
        privates[player]["shed"]["WHEAT"] = wheat[player]

    market = engine._new_market()
    market["inventory"]["WHEAT"] = inventory
    engine._refresh_prices(market)
    town = engine._new_town()
    states = []
    for player in range(2):
        states.append(
            SimpleNamespace(
                observation=SimpleNamespace(
                    market=market,
                    farms=farms,
                    private=privates[player],
                    town=town,
                ),
                action={"farmer": ["PASS"], "hands": [], "market": deepcopy(markets[player])},
            )
        )
    env = SimpleNamespace(
        configuration={
            "boardSize": 10,
            "maxMarketOrdersPerTurn": 10,
            "farmHandCostMult": 1,
            "shedCapacity": 100,
        }
    )
    engine._process_market(states, env)
    return {
        "farms": deepcopy(farms),
        "privates": deepcopy(privates),
        "market": deepcopy(market),
        "town": deepcopy(town),
    }


def _without_money(snapshot: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(snapshot)
    for farm in result["farms"]:
        farm.pop("money", None)
    return result


def _case(engine, *, own_player: int, rival_op: str) -> dict[str, Any]:
    if own_player not in (0, 1):
        raise ValueError("own_player must be 0 or 1")
    if rival_op not in ("BUY_PRODUCT", "SELL"):
        raise ValueError("rival_op must be BUY_PRODUCT or SELL")
    rival_player = 1 - own_player

    own_baseline = [
        ["SELL", "WHEAT", 1],
        [],
        ["BUY_PRODUCT", "WHEAT", 1],
    ]
    own_cancelled = [[], [], []]
    rival = [[], [rival_op, "WHEAT", 1], []]

    baseline_markets = [[], []]
    cancelled_markets = [[], []]
    baseline_markets[own_player] = own_baseline
    baseline_markets[rival_player] = rival
    cancelled_markets[own_player] = own_cancelled
    cancelled_markets[rival_player] = rival

    starting_wheat = [0, 0]
    starting_wheat[own_player] = 1
    starting_wheat[rival_player] = 0 if rival_op == "BUY_PRODUCT" else 1

    baseline = _execute(engine, baseline_markets, wheat=tuple(starting_wheat))
    cancelled = _execute(engine, cancelled_markets, wheat=tuple(starting_wheat))
    state_equal = _without_money(baseline) == _without_money(cancelled)
    own_delta = cancelled["farms"][own_player]["money"] - baseline["farms"][own_player]["money"]
    rival_delta = cancelled["farms"][rival_player]["money"] - baseline["farms"][rival_player]["money"]

    if not state_equal:
        verdict = "STATE_DIVERGENCE"
    elif own_delta > 0 and rival_delta <= 0:
        verdict = "REPLAY_BENEFIT"
    elif own_delta < 0:
        verdict = "REPLAY_HARM"
    elif own_delta == 0 and rival_delta == 0:
        verdict = "REPLAY_NEUTRAL"
    else:
        verdict = "MIXED_CASH_EFFECT"

    return {
        "own_player": own_player,
        "rival_player": rival_player,
        "rival_operation": rival_op,
        "baseline_actions": baseline_markets,
        "cancelled_actions": cancelled_markets,
        "terminal_non_money_state_equal": state_equal,
        "baseline": {
            "own_money": baseline["farms"][own_player]["money"],
            "rival_money": baseline["farms"][rival_player]["money"],
            "own_wheat": baseline["privates"][own_player]["shed"]["WHEAT"],
            "rival_wheat": baseline["privates"][rival_player]["shed"]["WHEAT"],
            "market_wheat": baseline["market"]["inventory"]["WHEAT"],
        },
        "cancelled": {
            "own_money": cancelled["farms"][own_player]["money"],
            "rival_money": cancelled["farms"][rival_player]["money"],
            "own_wheat": cancelled["privates"][own_player]["shed"]["WHEAT"],
            "rival_wheat": cancelled["privates"][rival_player]["shed"]["WHEAT"],
            "market_wheat": cancelled["market"]["inventory"]["WHEAT"],
        },
        "cancelled_minus_baseline": {
            "own_money": own_delta,
            "rival_money": rival_delta,
        },
        "verdict": verdict,
    }


def _price_floor_case(engine, *, own_player: int = 0) -> dict[str, Any]:
    rival_player = 1 - own_player
    baseline_markets = [[], []]
    cancelled_markets = [[], []]
    baseline_markets[own_player] = [
        ["SELL", "WHEAT", 1],
        [],
        ["BUY_PRODUCT", "WHEAT", 1],
    ]
    baseline_markets[rival_player] = [[], [], []]
    cancelled_markets[own_player] = [[], [], []]
    cancelled_markets[rival_player] = [[], [], []]
    wheat = [0, 0]
    wheat[own_player] = 1
    starting_inventory = 1_000_000_000
    baseline = _execute(
        engine,
        baseline_markets,
        wheat=tuple(wheat),
        inventory=starting_inventory,
    )
    cancelled = _execute(
        engine,
        cancelled_markets,
        wheat=tuple(wheat),
        inventory=starting_inventory,
    )
    return {
        "own_player": own_player,
        "starting_inventory": starting_inventory,
        "terminal_non_money_state_equal": _without_money(baseline) == _without_money(cancelled),
        "baseline_market_wheat": baseline["market"]["inventory"]["WHEAT"],
        "cancelled_market_wheat": cancelled["market"]["inventory"]["WHEAT"],
        "baseline_own_wheat": baseline["privates"][own_player]["shed"]["WHEAT"],
        "cancelled_own_wheat": cancelled["privates"][own_player]["shed"]["WHEAT"],
        "baseline_own_money": baseline["farms"][own_player]["money"],
        "cancelled_own_money": cancelled["farms"][own_player]["money"],
        "reason": "SELL at price floor does not add market supply; later BUY still removes supply",
    }


def build_report() -> dict[str, Any]:
    engine, raw, blob = _load_engine()
    cases = {}
    for own_player in (0, 1):
        for rival_op, label in (("BUY_PRODUCT", "rival_buy"), ("SELL", "rival_sell")):
            cases[f"seat{own_player}_{label}"] = _case(
                engine, own_player=own_player, rival_op=rival_op
            )
    floor = _price_floor_case(engine)

    buy_cases = [case for name, case in cases.items() if name.endswith("rival_buy")]
    sell_cases = [case for name, case in cases.items() if name.endswith("rival_sell")]
    opponent_contingent = (
        all(case["terminal_non_money_state_equal"] for case in cases.values())
        and all(case["verdict"] == "REPLAY_BENEFIT" for case in buy_cases)
        and all(case["verdict"] == "REPLAY_HARM" for case in sell_cases)
        and not floor["terminal_non_money_state_equal"]
    )

    return {
        "schema": "titan-v3-self-cross-opponent-contingency/v1",
        "engine": {
            "path": str(ENGINE_PATH.relative_to(ROOT)),
            "git_blob": blob,
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        },
        "cases": cases,
        "price_floor_case": floor,
        "conclusion": {
            "opponent_contingent": opponent_contingent,
            "observed_replay_counterfactual_can_prove": "REPLAY_BENEFIT_OR_HARM_FOR_BOUND_TAPE",
            "runtime_dominance_proven": False,
            "runtime_requirement": (
                "all-rival-action certificate or an observable fail-closed condition; "
                "hidden simultaneous rival orders cannot be replaced by one replay tape"
            ),
            "verdict": "OPPONENT_CONTINGENT" if opponent_contingent else "INVALID_WITNESS",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-opponent-contingency", action="store_true")
    args = parser.parse_args()
    report = build_report()
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    print(encoded, end="")
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    if args.require_opponent_contingency and not report["conclusion"]["opponent_contingent"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
