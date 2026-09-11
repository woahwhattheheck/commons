#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""B4 audit: execute a conservative one-day-earlier native SHEEP chain.

This is evidence tooling, not a production candidate. The static tape linker first
requires one unambiguous day-9 native SHEEP buy whose actor-local PICKUP->PLACE units
balance exactly. The counterfactual then moves only those linked events 24 turns
earlier, without stealing authored work:

* BUY_ANIMAL/SHEEP is appended after incumbent market rows, preserving existing
  cash commitments;
* PICKUP/PLACE may replace only a literal parent PASS in the same actor slot;
* an original event is suppressed only after its shifted counterpart executed;
* every later shifted event requires all earlier linked events to have executed;
* the chain is enabled only when YARN_STORE is already public before the first
  shift, making V231's later day-9 sheep->cow substitution structurally
  impossible (that late gate requires no YARN_STORE among unlocked shops).

The official interpreter decides cash, shed capacity, positions, pasture legality,
pickup/place execution, service consequences, and terminal score. A failed
prerequisite is evidence against a blind tape move, never permission to weaken it.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
V3 = HERE.parents[1]
LAB = V3.parents[1]
OVERLAY = V3 / "overlay"
EVALUATOR = LAB / "reference" / "evaluator" / "evaluate.py"
ENGINE_DIR = LAB / "reference" / "engine"
R04 = OVERLAY / "r04_full_router.py"

FROZEN = "508b342fc46fa91e3d7cdc3f0b7e44934a187c14"
TURNS_PER_DAY = 24
ROUTE_STEP = 144
FINAL_PLAN_STEP = 648
MAX_ORDERS = 10
DAY9 = range(9 * TURNS_PER_DAY, 10 * TURNS_PER_DAY)
CHAIN_STOP = 12 * TURNS_PER_DAY
DEFAULT_SEEDS = tuple(range(2611151001, 2611151009))


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _strict_qty(row) -> int | None:
    if not (isinstance(row, list) and len(row) >= 3 and type(row[2]) is int and row[2] > 0):
        return None
    return row[2]


def _market(action):
    value = action.get("market", []) if isinstance(action, dict) else []
    return value if isinstance(value, list) else []


def _workers(action):
    if not isinstance(action, dict):
        return []
    farmer = action.get("farmer")
    hands = action.get("hands")
    if not isinstance(farmer, list) or not isinstance(hands, list):
        return []
    return [farmer, *hands]


def _worker_cmd(action, actor):
    workers = _workers(action)
    return workers[actor] if 0 <= actor < len(workers) else None


def _set_worker(action, actor, command):
    result = copy.deepcopy(action)
    workers = _workers(result)
    if actor < 0 or actor >= len(workers):
        raise IndexError(actor)
    workers[actor] = copy.deepcopy(command)
    result["farmer"] = workers[0]
    result["hands"] = workers[1:]
    return result


def _sheep_events(action):
    result = []
    for actor, command in enumerate(_workers(action)):
        if (
            isinstance(command, list)
            and len(command) >= 2
            and command[0] in ("PICKUP", "PLACE")
            and command[1] == "SHEEP"
        ):
            qty = 1 if len(command) < 3 else command[2]
            result.append((actor, command, qty if type(qty) is int and qty > 0 else None))
    return result


def _sheep_buy_rows(action):
    rows = []
    for index, row in enumerate(_market(action)):
        if isinstance(row, list) and len(row) >= 2 and row[:2] == ["BUY_ANIMAL", "SHEEP"]:
            rows.append((index, row, _strict_qty(row)))
    return rows


def _raw_target_ok(tape, event):
    target = event["target_step"]
    if target < 0 or target >= len(tape):
        return False, "target-out-of-range"
    action = tape[target]
    if event["kind"] == "buy":
        if _sheep_buy_rows(action):
            return False, "target-already-buys-sheep"
        occupied = len([row for row in _market(action) if isinstance(row, list) and row])
        return (occupied < MAX_ORDERS, "ok" if occupied < MAX_ORDERS else "target-market-full")
    command = _worker_cmd(action, event["actor"])
    return (command == ["PASS"], "ok" if command == ["PASS"] else "target-actor-authored-work")


def build_chain_spec(tape, plan: int) -> dict:
    """Link one day-9 SHEEP buy to an exact actor-local pickup/place chain."""
    buys = []
    for step in DAY9:
        for row_index, row, qty in _sheep_buy_rows(tape[step]):
            buys.append((step, row_index, copy.deepcopy(row), qty))
    if not buys:
        return {"plan": plan, "status": "no-day9-sheep-buy", "events": []}
    if len(buys) != 1 or buys[0][3] is None:
        return {"plan": plan, "status": "ambiguous-day9-buy", "events": []}

    buy_step, row_index, buy_row, units = buys[0]
    carried: dict[int, int] = {}
    placed = 0
    worker_events = []
    ambiguous = None
    complete_step = None
    for step in range(buy_step, min(CHAIN_STOP, len(tape))):
        if step != buy_step and _sheep_buy_rows(tape[step]):
            ambiguous = "second-sheep-buy-before-chain-complete"
            break
        for actor, command, qty in _sheep_events(tape[step]):
            if qty is None:
                ambiguous = "malformed-sheep-worker-quantity"
                break
            if command[0] == "PICKUP":
                carried[actor] = carried.get(actor, 0) + qty
                worker_events.append((step, actor, copy.deepcopy(command), qty))
            else:
                if carried.get(actor, 0) < qty:
                    ambiguous = "place-without-linked-actor-pickup"
                    break
                carried[actor] -= qty
                placed += qty
                worker_events.append((step, actor, copy.deepcopy(command), qty))
                if placed == units and all(value == 0 for value in carried.values()):
                    complete_step = step
                    break
                if placed > units:
                    ambiguous = "placed-more-than-bought"
                    break
        if ambiguous or complete_step is not None:
            break

    if ambiguous:
        return {"plan": plan, "status": ambiguous, "events": []}
    if complete_step is None or placed != units or any(carried.values()):
        return {"plan": plan, "status": "incomplete-pickup-place-chain", "events": []}

    events = [{
        "id": f"p{plan}-buy-{buy_step}",
        "kind": "buy",
        "source_step": buy_step,
        "target_step": buy_step - TURNS_PER_DAY,
        "row_index": row_index,
        "row": buy_row,
        "qty": units,
    }]
    for number, (step, actor, command, qty) in enumerate(worker_events):
        events.append({
            "id": f"p{plan}-worker-{number}-{step}-{actor}",
            "kind": command[0].lower(),
            "source_step": step,
            "target_step": step - TURNS_PER_DAY,
            "actor": actor,
            "command": command,
            "qty": qty,
        })

    seen_actor_targets = set()
    for event in events[1:]:
        key = (event["target_step"], event["actor"])
        if key in seen_actor_targets:
            return {"plan": plan, "status": "shifted-actor-slot-collision", "events": events}
        seen_actor_targets.add(key)
        if event["target_step"] <= events[0]["target_step"]:
            return {"plan": plan, "status": "worker-not-after-shifted-buy", "events": events}

    static_checks = []
    for event in events:
        ok, reason = _raw_target_ok(tape, event)
        static_checks.append({"event": event["id"], "ok": ok, "reason": reason})
    static_safe = all(row["ok"] for row in static_checks)
    return {
        "plan": plan,
        "status": "static-shiftable" if static_safe else "static-collision",
        "buy_units": units,
        "source_complete_step": complete_step,
        "events": events,
        "static_checks": static_checks,
        "static_safe": static_safe,
    }


def build_specs(tapes):
    return {plan: build_chain_spec(tape, plan) for plan, tape in enumerate(tapes)}


def _fresh_r04(tag: str):
    if str(OVERLAY) not in sys.path:
        sys.path.insert(0, str(OVERLAY))
    module = _load(R04, f"b4_r04_{tag}")
    agent = module.install(
        None,
        horizon=8,
        opening=0,
        row_order=True,
        evening_flush=True,
        sale_fertilizer=True,
        cattle_early=False,
    )
    return module, agent


def _plan(module, seat):
    policy = getattr(module, "_POLICY", None)
    if policy is None:
        return None
    state = policy.players.get(seat)
    return None if state is None else state.plan


def _sheep_total(observation, seat):
    farm = observation["farms"][seat]
    private = observation["private"]
    total = int(private["shed"].get("SHEEP", 0))
    total += sum(int(inv.get("SHEEP", 0)) for inv in private["inventories"])
    for row in farm["tiles"]:
        for tile in row:
            if isinstance(tile, dict) and tile.get("animal") == "SHEEP":
                total += 1
    return total


def _actor_sheep(observation, actor):
    inventories = observation["private"]["inventories"]
    if actor < 0 or actor >= len(inventories):
        return None
    return int(inventories[actor].get("SHEEP", 0))


def _position(observation, seat, actor):
    farm = observation["farms"][seat]
    positions = [farm["farmer"], *farm["hands"]]
    if actor < 0 or actor >= len(positions):
        return None
    value = positions[actor]
    if not (isinstance(value, list) and len(value) == 2 and all(type(v) is int for v in value)):
        return None
    return tuple(value)


def _tile(observation, seat, position):
    if position is None:
        return None
    x, y = position
    tiles = observation["farms"][seat]["tiles"]
    if y < 0 or y >= len(tiles) or x < 0 or x >= len(tiles[y]):
        return None
    return tiles[y][x]


def _shops(observation):
    town = observation.get("town", {})
    shops = town.get("unlocked_shops", []) if isinstance(town, dict) else []
    return list(shops) if isinstance(shops, list) else []


def _replace_one_market(action, row, replacement):
    market = _market(action)
    matches = [i for i, value in enumerate(market) if value == row]
    if len(matches) != 1:
        return None
    result = copy.deepcopy(action)
    result["market"][matches[0]] = copy.deepcopy(replacement)
    return result


class ShiftRuntime:
    def __init__(self, spec):
        self.spec = spec
        self.enabled = None
        self.success: dict[str, bool] = {}
        self.attempts = []
        self.suppression_failures = []
        self.first_target = min((e["target_step"] for e in spec.get("events", [])), default=None)

    def _prior_success(self, event):
        for prior in self.spec.get("events", []):
            if prior["target_step"] >= event["target_step"]:
                break
            if not self.success.get(prior["id"], False):
                return False
        return True

    def transform(self, action, observation, seat, step):
        if not self.spec.get("static_safe"):
            return action, []
        if self.first_target == step and self.enabled is None:
            self.enabled = "YARN_STORE" in _shops(observation)
        if not self.enabled:
            return action, []

        result = action
        pending = []
        for event in self.spec["events"]:
            if event["target_step"] != step or not self._prior_success(event):
                continue
            before = {
                "sheep_total": _sheep_total(observation, seat),
                "actor_sheep": _actor_sheep(observation, event.get("actor", -1)),
                "position": _position(observation, seat, event.get("actor", -1)),
                "money": observation["farms"][seat].get("money"),
                "shed_total": sum(observation["private"]["shed"].values()),
                "shops": _shops(observation),
            }
            if event["kind"] == "buy":
                market = _market(result)
                if len([row for row in market if isinstance(row, list) and row]) >= MAX_ORDERS:
                    self.success[event["id"]] = False
                    self.attempts.append({"event": event["id"], "step": step, "result": "runtime-market-full"})
                    continue
                result = copy.deepcopy(result)
                result.setdefault("market", []).append(copy.deepcopy(event["row"]))
            else:
                # Hour 23 is observationally ambiguous for PLACE: the official engine
                # auto-drops carried inventory at EOD, so an inventory decrease cannot
                # prove that the inserted PLACE executed. Do not inject an action whose
                # success cannot be distinguished from the EOD reset.
                if event["kind"] == "place" and step % TURNS_PER_DAY == TURNS_PER_DAY - 1:
                    self.success[event["id"]] = False
                    self.attempts.append({"event": event["id"], "step": step, "result": "runtime-eod-place-unverifiable"})
                    continue
                if _worker_cmd(result, event["actor"]) != ["PASS"]:
                    self.success[event["id"]] = False
                    self.attempts.append({"event": event["id"], "step": step, "result": "runtime-parent-not-pass"})
                    continue
                result = _set_worker(result, event["actor"], event["command"])
            pending.append((event, before))

        for event in self.spec.get("events", []):
            if event["source_step"] != step or not self.success.get(event["id"], False):
                continue
            if event["kind"] == "buy":
                changed = _replace_one_market(result, event["row"], [])
                if changed is None:
                    self.suppression_failures.append({"event": event["id"], "step": step, "kind": "buy"})
                else:
                    result = changed
            else:
                if _worker_cmd(result, event["actor"]) != event["command"]:
                    self.suppression_failures.append({"event": event["id"], "step": step, "kind": event["kind"]})
                else:
                    result = _set_worker(result, event["actor"], ["PASS"])
        return result, pending

    def observe(self, pending, after_observation, seat, step):
        for event, before in pending:
            if event["kind"] == "buy":
                ok = _sheep_total(after_observation, seat) >= before["sheep_total"] + event["qty"]
            elif event["kind"] == "pickup":
                after = _actor_sheep(after_observation, event["actor"])
                ok = after is not None and before["actor_sheep"] is not None and after >= before["actor_sheep"] + event["qty"]
            elif event["kind"] == "place" and step % TURNS_PER_DAY == TURNS_PER_DAY - 1:
                # Defensive provenance guard: even a stale/manually-constructed
                # pending record at EOD must never be certified by inventory reset.
                ok = False
            else:
                after = _actor_sheep(after_observation, event["actor"])
                tile = _tile(after_observation, seat, before["position"])
                ok = (
                    after is not None
                    and before["actor_sheep"] is not None
                    and after <= before["actor_sheep"] - event["qty"]
                    and isinstance(tile, dict)
                    and tile.get("animal") == "SHEEP"
                    and tile.get("placed_day") == step // TURNS_PER_DAY
                )
            self.success[event["id"]] = bool(ok)
            row = dict(before)
            row.update({"event": event["id"], "kind": event["kind"], "step": step, "result": "executed" if ok else "engine-rejected"})
            self.attempts.append(row)

    def report(self):
        events = self.spec.get("events", [])
        return {
            "plan": self.spec.get("plan"),
            "static_status": self.spec.get("status"),
            "enabled_by_yarn_guard": self.enabled,
            "all_shifted_events_executed": bool(events) and all(self.success.get(e["id"], False) for e in events),
            "success": dict(self.success),
            "attempts": self.attempts,
            "suppression_failures": self.suppression_failures,
        }


def _configuration(evalmod, engine, seed):
    cfg = evalmod.Struct({
        key: value.get("default") if isinstance(value, dict) else value
        for key, value in engine.specification["configuration"].items()
    })
    cfg.seed = seed
    return cfg


def _run_game(evalmod, engine, seed, candidate_seat, specs, shifted):
    cfg = _configuration(evalmod, engine, seed)
    env = evalmod.Struct(configuration=cfg, done=False, info={})
    state = [evalmod.Struct(observation=evalmod.Struct(), action={}, status="ACTIVE", reward=0) for _ in range(2)]
    engine.interpreter(state, env)
    if cfg.get("seed") is not None:
        raise AssertionError("engine exposed seed after initialization")

    loaded = [_fresh_r04(f"{seed}_{candidate_seat}_{int(shifted)}_{seat}") for seat in range(2)]
    runtime = None
    trace = hashlib.sha256()
    chosen_plan = None
    for step in range(int(cfg.episodeSteps)):
        actions = []
        pending = []
        for seat, (module, agent) in enumerate(loaded):
            observation = state[seat].observation
            observation.step = step
            observation.remainingOverageTime = 0
            action = agent(observation, cfg)
            if not isinstance(action, dict):
                raise AssertionError("parent returned non-object action")
            plan = _plan(module, seat)
            if seat == candidate_seat and plan is not None:
                if ROUTE_STEP <= step < FINAL_PLAN_STEP:
                    chosen_plan = plan
                may_rebind = (
                    runtime is None
                    or (
                        runtime.spec.get("plan") != plan
                        and not runtime.attempts
                        and (runtime.first_target is None or step < runtime.first_target)
                    )
                )
                if may_rebind:
                    runtime = ShiftRuntime(specs.get(plan, {"plan": plan, "status": "missing-spec", "events": []}))
                if shifted and runtime is not None:
                    action, seat_pending = runtime.transform(action, observation, seat, step)
                    pending.extend((seat, event, before) for event, before in seat_pending)
            actions.append(action)
        for seat in range(2):
            state[seat].action = actions[seat]
        trace.update(json.dumps({"step": step, "actions": actions}, sort_keys=True, separators=(",", ":")).encode())
        engine.interpreter(state, env)
        if shifted and runtime is not None:
            grouped = [(event, before) for seat, event, before in pending if seat == candidate_seat]
            runtime.observe(grouped, state[candidate_seat].observation, candidate_seat, step)
        if all(row.status == "DONE" for row in state):
            return {
                "seed": seed,
                "candidate_seat": candidate_seat,
                "plan": chosen_plan,
                "scores": [row.reward for row in state],
                "trace_sha256": trace.hexdigest(),
                "shift": runtime.report() if runtime is not None else None,
            }
    raise AssertionError("game did not terminate")


def _margin(game):
    seat = game["candidate_seat"]
    return float(game["scores"][seat]) - float(game["scores"][1 - seat])


def _classify_cells(cells):
    shifted = [row for row in cells if row.get("shift")]
    activated = [row for row in shifted if row["shift"].get("all_shifted_events_executed")]
    negative = [row for row in activated if row["delta_margin"] < 0]
    positive = [row for row in activated if row["delta_margin"] > 0]
    if any(row["shift"].get("suppression_failures") for row in shifted):
        disposition = "REJECT_SUPPRESSION_PROVENANCE_MISMATCH"
    elif not activated:
        disposition = "NO_RUNTIME_COMPLETE_CHAIN_ON_PANEL"
    elif negative:
        disposition = "HOLD_RUNTIME_CHAIN_HAS_NEGATIVE_CELL"
    elif positive:
        disposition = "PROMISING_FULLCHAIN_RUNTIME_WIDEN_REQUIRED"
    else:
        disposition = "HOLD_FULLCHAIN_EXECUTES_WITHOUT_MONEY_GAIN"
    return activated, negative, positive, disposition


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", default=",".join(map(str, DEFAULT_SEEDS)))
    args = parser.parse_args(argv)
    seeds = tuple(int(value) for value in args.seeds.split(",") if value)
    if not seeds:
        raise SystemExit("at least one seed is required")

    evalmod = _load(EVALUATOR, "b4_official_evaluator")
    engine, engine_hashes = evalmod.get_engine(ENGINE_DIR)
    template_module, _ = _fresh_r04("template")
    specs = build_specs(template_module._INLINE_TAPES)

    cells = []
    for seed in seeds:
        for seat in (0, 1):
            control = _run_game(evalmod, engine, seed, seat, specs, shifted=False)
            candidate = _run_game(evalmod, engine, seed, seat, specs, shifted=True)
            if control["plan"] != candidate["plan"]:
                raise AssertionError(("route-plan-drift", seed, seat, control["plan"], candidate["plan"]))
            cells.append({
                "seed": seed,
                "candidate_seat": seat,
                "plan": candidate["plan"],
                "control_scores": control["scores"],
                "candidate_scores": candidate["scores"],
                "control_trace_sha256": control["trace_sha256"],
                "candidate_trace_sha256": candidate["trace_sha256"],
                "delta_margin": _margin(candidate) - _margin(control),
                "shift": candidate["shift"],
            })

    activated, negative, positive, disposition = _classify_cells(cells)

    report = {
        "schema": "titan-v31-b4-fullchain-feasibility/v1",
        "truth_boundary": "Frozen-508b source audit with cattle_early OFF; not current-a612 package or promotion authority.",
        "frozen_source": FROZEN,
        "engine_ref": evalmod.ENGINE_REF,
        "engine_sha256": engine_hashes,
        "seeds": list(seeds),
        "static_specs": specs,
        "cells": cells,
        "summary": {
            "cells": len(cells),
            "runtime_complete_chain_cells": len(activated),
            "positive_complete_cells": len(positive),
            "negative_complete_cells": len(negative),
            "plans_seen": sorted({row["plan"] for row in cells if row["plan"] is not None}),
            "plans_static_shiftable": sorted(plan for plan, spec in specs.items() if spec.get("static_safe")),
            "disposition": disposition,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("B4_FULLCHAIN", json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
