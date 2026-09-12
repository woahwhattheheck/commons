#!/usr/bin/env python3
"""Current-native census for C5 predictable rival procurement collisions.

This runner reuses the process-isolated official-interpreter field harness. It
never exposes the rival's current action to the policy. A passive engine observer
sees both returned actions only after both actors have committed their callback,
then validates the source-authenticated, route-invariant Arlene pulse atlas.

No action is rewritten. Results are prevalence/custody evidence only.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import predictable_procurement as predictor

HERE = Path(__file__).resolve().parent
V4 = HERE.parents[1]
S8_RUNNER = V4 / "repairs" / "gameplay" / "s8-egg-care" / "run_s8_field.py"
S8_RUNNER_GIT_BLOB = "bc92ff59cc9dccaeda3b7435f1ec2aca86bcde68"
DEFAULT_SEEDS = (17, 9922999, 2026091201)


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _copy_json(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))


def _market(action: Any) -> list[Any]:
    if not isinstance(action, dict):
        return []
    market = action.get("market", [])
    return list(market) if isinstance(market, list) else []


def _row_is(order: Any, op: str, item: str, qty: int | None = None) -> bool:
    if not isinstance(order, list) or len(order) < 2 or order[0] != op or order[1] != item:
        return False
    if qty is None:
        return True
    return len(order) >= 3 and type(order[2]) is int and order[2] == qty


def _blank_at(rows: list[Any], row: int) -> bool:
    return row >= len(rows) or not rows[row]


def _event_candidates(own_rows: list[Any], pulse: dict[str, Any], max_orders: int) -> dict[str, Any]:
    row = int(pulse["row"])
    item = str(pulse["item"])
    buys = [i for i, raw in enumerate(own_rows[:max_orders]) if _row_is(raw, "BUY_PRODUCT", item)]
    sells = [i for i, raw in enumerate(own_rows[:max_orders]) if _row_is(raw, "SELL", item)]
    aligned_buy = row in buys
    same_row_sell = row in sells
    later_sells = [i for i in sells if i > row]
    realign = [i for i in buys if i != row] if row < max_orders and _blank_at(own_rows, row) else []
    delay_target = row + 1
    delay_sell = bool(
        same_row_sell
        and delay_target < max_orders
        and _blank_at(own_rows, delay_target)
    )
    return {
        "own_same_item_buy_rows": buys,
        "own_same_item_sell_rows": sells,
        "natural_cobuy_row": aligned_buy,
        "crosssell_same_row": same_row_sell,
        "crosssell_already_after": later_sells,
        "cobuy_realign_source_rows": realign,
        "crosssell_delay_one_row_candidate": delay_sell,
    }


def _install_market_census(runner, atlas: dict[str, Any]):
    base_census = runner.Census
    base_install = runner.install_observers
    max_orders = int(atlas["scope"]["max_market_rows"])
    by_step: dict[int, list[dict[str, Any]]] = {}
    for pulse in atlas["invariant_pulses"]:
        by_step.setdefault(int(pulse["step"]), []).append(dict(pulse))

    class MarketCensus(base_census):
        def __init__(self, seat):
            super().__init__(seat)
            self.market_counts = Counter()
            self.market_events: list[dict[str, Any]] = []

        def observe_market(self, step: int, actions: list[Any], fills: list[dict[str, Any]]):
            pulses = by_step.get(step, ())
            if not pulses:
                return
            rival = 1 - self.seat
            own_rows = _market(actions[self.seat])
            rival_rows = _market(actions[rival])
            for pulse in pulses:
                row = int(pulse["row"])
                item = str(pulse["item"])
                qty = int(pulse["qty"])
                self.market_counts["prediction_checks"] += 1
                actual = rival_rows[row] if row < len(rival_rows) else None
                matched = _row_is(actual, "BUY_PRODUCT", item, qty)
                self.market_counts["prediction_matches"] += int(matched)
                self.market_counts["prediction_mismatches"] += int(not matched)

                rival_item_orders = [
                    i for i, raw in enumerate(rival_rows[:max_orders])
                    if _row_is(raw, "BUY_PRODUCT", item)
                ]
                fill_prices = [
                    int(f["price"]) for f in fills
                    if f["seat"] == rival and f["op"] == "BUY_PRODUCT" and f["item"] == item
                ]
                if len(rival_item_orders) == 1:
                    self.market_counts["unambiguous_rival_filled_units"] += len(fill_prices)
                else:
                    self.market_counts["ambiguous_same_item_fill_events"] += int(bool(fill_prices))

                candidates = _event_candidates(own_rows, pulse, max_orders)
                self.market_counts["natural_cobuy_rows"] += int(candidates["natural_cobuy_row"])
                self.market_counts["crosssell_same_rows"] += int(candidates["crosssell_same_row"])
                self.market_counts["crosssell_already_after_rows"] += len(candidates["crosssell_already_after"])
                self.market_counts["cobuy_realign_candidates"] += len(candidates["cobuy_realign_source_rows"])
                self.market_counts["crosssell_delay_candidates"] += int(
                    candidates["crosssell_delay_one_row_candidate"]
                )
                if len(self.market_events) < 128:
                    self.market_events.append({
                        "step": step,
                        "pulse": dict(pulse),
                        "prediction_match": matched,
                        "rival_returned_row": _copy_json(actual),
                        "rival_same_item_buy_rows": rival_item_orders,
                        "rival_same_item_fill_units": len(fill_prices),
                        "rival_same_item_fill_prices": fill_prices,
                        "own_market": _copy_json(own_rows[:max_orders]),
                        "candidates": candidates,
                    })

        def result(self):
            base = super().result()
            base["predictable_procurement"] = {
                "counts": dict(self.market_counts),
                "samples": self.market_events,
                "policy_authority": False,
                "hidden_current_rival_action_used_by_policy": False,
            }
            return base

    def install(engine, census, own_farm, own_private):
        originals = base_install(engine, census, own_farm, own_private)
        wrapped_market = engine._process_market
        base_commit = engine._commit_unit

        def market(state, env):
            step = int(getattr(state[0].observation, "step", 0))
            actions = [_copy_json(s.action if isinstance(s.action, dict) else {}) for s in state]
            private_to_seat = {id(s.observation.private): i for i, s in enumerate(state)}
            fills: list[dict[str, Any]] = []

            def commit(op, item, price, farm, private, market_obj, shed_capacity=100):
                ok = base_commit(op, item, price, farm, private, market_obj, shed_capacity)
                if ok:
                    seat = private_to_seat.get(id(private))
                    if seat is None:
                        raise RuntimeError("market commit private object lost seat custody")
                    fills.append({
                        "seat": seat,
                        "op": op,
                        "item": item,
                        "price": int(price),
                    })
                return ok

            engine._commit_unit = commit
            try:
                result = wrapped_market(state, env)
            finally:
                engine._commit_unit = base_commit
            census.observe_market(step, actions, fills)
            return result

        engine._process_market = market
        return originals

    runner.Census = MarketCensus
    runner.install_observers = install


def _compact_game(game: dict[str, Any]) -> dict[str, Any]:
    keys = ("seed", "seat", "status", "steps", "scores", "margin", "failure",
            "trace_sha256", "action_sha256", "world_sha256", "wall_seconds")
    result = {key: game.get(key) for key in keys}
    result["predictable_procurement"] = (game.get("census") or {}).get("predictable_procurement")
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runtime", type=Path, required=True)
    ap.add_argument("--opponent", type=Path, required=True,
                    help="Directory containing exact vendored Arlene as main.py")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--seeds", default=",".join(map(str, DEFAULT_SEEDS)))
    args = ap.parse_args(argv)

    if predictor.git_blob(S8_RUNNER.read_bytes()) != S8_RUNNER_GIT_BLOB:
        raise ValueError("shared current-native runner Git blob drifted")
    opponent_main = args.opponent.resolve() / "main.py"
    arlene = predictor.load_arlene(opponent_main, c5_oracle=predictor.default_c5_oracle_path())
    atlas = predictor.analyze(arlene)
    runner = load(S8_RUNNER, "c5_predictable_shared_runner")
    _install_market_census(runner, atlas)

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    seeds = tuple(int(x.strip()) for x in args.seeds.split(",") if x.strip())
    if not seeds:
        raise ValueError("at least one seed is required")

    cells = []
    for seed in seeds:
        for seat in (0, 1):
            cell_dir = output / f"seed-{seed}-seat-{seat}"
            game = runner.play(
                args.runtime.resolve(),
                seed,
                seat,
                cell_dir,
                opponent=args.opponent.resolve(),
                passive=True,
            )
            cells.append(_compact_game(game))

    totals = Counter()
    complete = 0
    for cell in cells:
        complete += int(cell["status"] == "complete")
        telemetry = cell.get("predictable_procurement") or {}
        totals.update(telemetry.get("counts") or {})

    candidate_total = sum(totals.get(key, 0) for key in (
        "natural_cobuy_rows",
        "crosssell_same_rows",
        "crosssell_already_after_rows",
        "cobuy_realign_candidates",
        "crosssell_delay_candidates",
    ))
    if complete != len(cells):
        classification = "INVALID_INCOMPLETE"
    elif totals.get("prediction_mismatches", 0):
        classification = "INVALID_PREDICTOR_MISMATCH"
    elif totals.get("prediction_checks", 0) == 0:
        classification = "COLD_NO_ROUTE_INVARIANT_PULSE"
    elif totals.get("unambiguous_rival_filled_units", 0) == 0:
        classification = "COLD_NO_FILLED_PULSE"
    elif candidate_total == 0:
        classification = "COLD_NO_OWN_COLLISION"
    else:
        classification = "ENGAGED_CENSUS_ONLY"

    summary = {
        "requested_cells": len(cells),
        "complete_cells": complete,
        "classification": classification,
        "candidate_collision_total": candidate_total,
        **dict(sorted(totals.items())),
    }
    result = {
        "schema": "titan-v4-c5-predictable-procurement-field/v1",
        "method": "current native vs exact vendored Arlene, both seats, official interpreter, passive post-action market observer",
        "atlas": atlas,
        "seeds": list(seeds),
        "cells": cells,
        "summary": summary,
        "limits": [
            "No returned action is rewritten in this runner.",
            "The policy never receives the rival's current private action.",
            "Only route-invariant raw-index-stable Arlene pulses are predictor-authoritative.",
            "Candidate collision counts are not economic acceptance or activation authority.",
            "Any policy successor still requires exact counterfactual state custody, OFF identity, and paired both-seat economics.",
        ],
    }
    (output / "C5-PREDICTABLE-PROCUREMENT-FIELD.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True, allow_nan=False))
    return int(classification.startswith("INVALID_"))


if __name__ == "__main__":
    raise SystemExit(main())
